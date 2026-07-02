import os
import io
import time
import uuid
import traceback
import shutil
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

import pandas as pd
from proposal_engine import generate_pdf_from_data
from ai_engine import generate_ai_portfolio
from intelligent_parser import parse_messy_excel

# Safe print wrapper globally to prevent Errno 22 in all modules during background execution
import builtins
_orig_print = builtins.print
def safe_print(*args, **kwargs):
    try:
        with open("flask_app.log", "a", encoding="utf-8") as f:
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            f.write(sep.join(map(str, args)) + end)
    except Exception:
        pass
    try:
        if 'flush' not in kwargs:
            kwargs['flush'] = True
        _orig_print(*args, **kwargs)
    except OSError:
        pass
builtins.print = safe_print

# Also redirect stderr to the log file so tracebacks and raw exceptions are captured, and output to the original console
import sys
class _StderrLogger:
    def write(self, msg):
        if msg.strip():
            try:
                with open("flask_app.log", "a", encoding="utf-8") as f:
                    f.write(msg if msg.endswith("\n") else msg + "\n")
            except Exception:
                pass
            try:
                sys.__stderr__.write(msg)
                sys.__stderr__.flush()
            except Exception:
                pass
    def flush(self):
        try:
            sys.__stderr__.flush()
        except Exception:
            pass
sys.stderr = _StderrLogger()


def get_memory_usage():
    try:
        import os
        if os.name == 'nt':
            import subprocess
            import csv
            pid = os.getpid()
            out = subprocess.check_output(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH']).decode('utf-8', errors='ignore')
            reader = csv.reader([out.strip()])
            row = next(reader)
            if len(row) >= 5:
                mem_str = row[4].replace(' K', '').replace(' KB', '').replace(',', '').strip()
                return float(mem_str) / 1024
        else:
            try:
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            return float(line.split()[1]) / 1024
            except Exception:
                import resource
                return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except Exception:
        pass
    return 0.0

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Increase Flask upload limit to 20MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

# Workspace paths
DEFAULT_EXCEL_PATH = "CLIENT_TEMPLATE.xlsx"
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")

# Ensure uploads folder exists
os.makedirs(UPLOADS_DIR, exist_ok=True)

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    print("[DEBUG ERROR] Upload failed: File size exceeds the 20MB limit.")
    return jsonify({"error": "File size exceeds the 20MB limit. Please upload a smaller file."}), 413

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "AI Portfolio Recommendation Engine API is active."})

@app.route("/api/log", methods=["POST"])
def client_log():
    data = request.json or {}
    print(f"[CLIENT LOG] {data.get('msg')}")
    return jsonify({"status": "ok"})


@app.route("/upload", methods=["POST"])
def upload_file():
    """Receives Excel file upload, stores it in uploads/, parses messy structures, and returns JSON metadata."""
    print("[DEBUG] Received file upload request on /upload")
    if "file" not in request.files:
        print("[DEBUG ERROR] No 'file' key found in request.files")
        return jsonify({"error": "No file uploaded in form data"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        print("[DEBUG ERROR] Empty filename selected")
        return jsonify({"error": "No file selected"}), 400
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".xlsx", ".xls"]:
        print(f"[DEBUG ERROR] Invalid file format: {ext}")
        return jsonify({"error": "Invalid file format. Only Excel spreadsheets (.xlsx, .xls) are allowed."}), 400
    
    filepath = None
    try:
        # Secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{int(time.time())}_{uuid.uuid4().hex[:4]}_{filename}"
        filepath = os.path.join(UPLOADS_DIR, unique_filename)
        file.save(filepath)
        print(f"[DEBUG] Secure file saved to: {filepath}")
        
        # Check for optional API Key header
        api_key = request.headers.get("X-Gemini-Key")
        
        # Check workflow header
        workflow = request.headers.get("X-Workflow", "recommendation")
        
        if workflow == "review":
            from review_engine import parse_review_excel
            parsed_data = parse_review_excel(filepath)
            
            client_name = parsed_data["client"].get("client_name", "Valued Client")
            portfolio_corpus = parsed_data["client"].get("portfolio_value_inr", 0.0)
            
            holdings_list = []
            for h in parsed_data.get("holdings", []):
                holdings_list.append({
                    "name": h.get("product_name", "Unnamed Holding"),
                    "class": h.get("asset_class", "Mutual Fund"),
                    "allocation_pct": h.get("allocation_pct", 0.0),
                    "gain_loss_pct": h.get("gain_loss_pct", 0.0)
                })
                
            return jsonify({
                "status": "success",
                "workflow": "review",
                "client_name": client_name,
                "corpus": f"{int(portfolio_corpus):,}" if portfolio_corpus > 0.0 else "0",
                "funds": holdings_list,
                "analytics": parsed_data.get("analytics"),
                "filepath": filepath,
                "proposal_data": parsed_data,
                "message": f"'{file.filename}' parsed as Portfolio Review successfully!"
            })
            
        # Parse messy excel using intelligent parser
        parsed_data = parse_messy_excel(filepath, api_key=api_key)
        
        # Enforce that at least one product is detected (Requirement 2)
        if not parsed_data.get("products") or len(parsed_data["products"]) == 0:
            raise ValueError("Parser failed: No investment products detected.")
        
        client_name = parsed_data["client"].get("Client Name", "Valued Client")
        portfolio_corpus = parsed_data["client"].get("Portfolio Corpus (INR)", "0")
        
        funds_list = []
        for p in parsed_data.get("products", []):
            funds_list.append({
                "name": p.get("Product Name", "Unnamed Product"),
                "class": p.get("Asset Class", "Mutual Fund")
            })
            
        return jsonify({
            "status": "success",
            "client_name": client_name,
            "corpus": portfolio_corpus,
            "sheets": parsed_data["sheets"],
            "allocation_columns": parsed_data["allocation_columns"],
            "products_columns": parsed_data["products_columns"],
            "funds": funds_list,
            "missing_fields": parsed_data["missing_fields"],
            "filepath": filepath,
            "proposal_data": parsed_data,
            "message": f"'{file.filename}' uploaded and parsed successfully!"
        })
    except ValueError as ve:
        print(f"[DEBUG ERROR] Parsing validation failed: {str(ve)}")
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"[DEBUG ERROR] Unexpected processing failure: {str(e)}")
        traceback.print_exc()
        print(f"[TRACEBACK]\n{traceback.format_exc()}")

        if filepath and os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"Failed to parse Excel spreadsheet: {str(e)}"}), 500

@app.route("/generate-proposal", methods=["POST"])
def generate_proposal_route():
    print(f"[MEMORY PROFILE] 1. Request received: {get_memory_usage():.2f} MB")
    print("[DEBUG] Request received.")
    print("\n[DEBUG] ==================================================")
    print("[DEBUG] Flask API: Received request on /generate-proposal")
    print("[DEBUG] ==================================================")
    
    data = request.json
    if not data:
        print("[DEBUG ERROR] Request payload is missing or empty JSON.")
        return jsonify({"error": "Missing JSON request payload"}), 400
        
    proposal_data = data.get("proposal_data")
    filepath = data.get("filepath")
    
    try:
        workflow = request.headers.get("X-Workflow", "recommendation")
        
        # Load from sent data or fallback to parsing the file
        if not proposal_data:
            if not filepath or not os.path.exists(filepath):
                print(f"[DEBUG ERROR] Referenced Excel file not found: {filepath}")
                return jsonify({"error": "Referenced Excel file not found. Please upload again."}), 404
            print(f"[MEMORY PROFILE] 2. Excel loaded: {get_memory_usage():.2f} MB")
            print(f"[DEBUG] Parsing Excel file: {filepath} for workflow: {workflow}")
            if workflow == "review":
                from review_engine import parse_review_excel
                proposal_data = parse_review_excel(filepath)
            else:
                proposal_data = parse_messy_excel(filepath)
            print(f"[MEMORY PROFILE] 3. Excel parsed: {get_memory_usage():.2f} MB")
            print("[DEBUG] Excel parsed successfully.")
        else:
            print(f"[MEMORY PROFILE] 2. Excel loaded (pre-parsed): {get_memory_usage():.2f} MB")
            print(f"[MEMORY PROFILE] 3. Excel parsed (pre-parsed): {get_memory_usage():.2f} MB")
            print("[DEBUG] Excel parsed successfully.")
                
        if workflow == "review":
            from review_engine import generate_review_narratives
            import review_pdf_engine
            print("[DEBUG] Imported review_pdf_engine absolute path:", os.path.abspath(review_pdf_engine.__file__))
            from review_pdf_engine import generate_review_pdf
            
            # Check for optional API Key
            api_key = request.headers.get("X-Gemini-Key")
            
            print("[DEBUG] Portfolio Review Generation started...")
            print("[DEBUG] AI generation started.")
            # Generate AI review narratives
            narratives = generate_review_narratives(proposal_data, api_key=api_key)
            proposal_data["ai_narratives"] = narratives
            print("[DEBUG] AI generation completed.")
            
            # Generate the Review PDF inside uploads/
            pdf_filename = f"Review_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = os.path.join(UPLOADS_DIR, pdf_filename)
 
            print("[DEBUG] proposal_engine.py started.")
            print(f"[DEBUG] Review PDF generation started. Saving file to: {pdf_filename}")
            generate_review_pdf(proposal_data, pdf_path)
            print(f"[DEBUG] Review PDF generation completed. Output file: {pdf_filename}")
            print("[DEBUG] PDF generated successfully.")
            
            # Clean up source Excel file from uploads/
            try:
                if filepath and os.path.exists(filepath):
                    os.remove(filepath)
                    print(f"[DEBUG] Deleted temporary excel source: {filepath}")
            except Exception as err:
                print(f"[DEBUG WARN] Failed to delete temporary source file: {str(err)}")
                
            return jsonify({
                "status": "success",
                "pdf_url": f"/api/download_pdf?file={pdf_filename}"
            })
            
        client_data = proposal_data.get("client", {})
        fund_data = proposal_data.get("products", [])
        
        # Check for optional API Key
        api_key = request.headers.get("X-Gemini-Key")
        if not api_key:
            print("[DEBUG] AI API Key is missing. Local rules-based fallback will be used.")
        else:
            print("[DEBUG] AI API Key detected. Engaging Gemini generative model.")
            
        # Run AI Optimization
        print("[DEBUG] AI generation started.")
        print("[DEBUG] AI processing started (auto-allocating funds and writing rationales)...")
        ai_portfolio = generate_ai_portfolio(client_data, fund_data, api_key=api_key)
        print("[DEBUG] AI processing completed successfully.")
        print("[DEBUG] AI generation completed.")
        print("[DEBUG] AI response received. Merging with firm settings and profiles.")
        
        merged_data = {
            "firm": proposal_data.get("firm", {}),
            "client": client_data,
            "portfolio_theme": ai_portfolio.get("portfolio_theme", ""),
            "allocation": ai_portfolio.get("allocation", []),
            "products": ai_portfolio.get("products", []),
            "executive_summary": ai_portfolio.get("executive_summary", ""),
            "portfolio_thesis": ai_portfolio.get("portfolio_thesis", ""),
            "market_commentary": ai_portfolio.get("market_commentary", ""),
            "has_swp": proposal_data.get("has_swp", False)
        }
        
        # Print parsed investment data in terminal logs (Requirement 6 & 7)
        print("\n[DEBUG] ==================================================", flush=True)
        print("[DEBUG] PARSED INVESTMENT DATA FOR PDF GENERATION:", flush=True)
        print(f"[DEBUG] Client Name: {client_data.get('Client Name')}", flush=True)
        print(f"[DEBUG] Portfolio Corpus: {client_data.get('Portfolio Corpus (INR)')}", flush=True)
        print(f"[DEBUG] Total Products Detected: {len(fund_data)}", flush=True)
        for idx, p in enumerate(fund_data, 1):
            print(f"[DEBUG]   Product {idx}: {p.get('Product Name')} | Asset Class: {p.get('Asset Class')} | Segment: {p.get('Segment')} | Amount: {p.get('Allocation (INR)')} | Target Return: {p.get('Target Return')}", flush=True)
        print("[DEBUG] Asset Allocation Dashboard Segments:", flush=True)
        for idx, a in enumerate(merged_data.get("allocation", []), 1):
            print(f"[DEBUG]   Segment {idx}: {a.get('Segment Name')} | Allocation: {a.get('Allocation %')}% | Objective: {a.get('Objective')}", flush=True)
        print("[DEBUG] ==================================================\n", flush=True)
        
        # Enforce that generated portfolio is not empty (Requirement 2)
        if not merged_data.get("products") or len(merged_data["products"]) == 0:
            raise ValueError("Parser failed: No investment products detected.")
        
        # Generate the PDF file inside uploads/
        pdf_filename = f"Proposal_{uuid.uuid4().hex[:8]}.pdf"
        pdf_path = os.path.join(UPLOADS_DIR, pdf_filename)
        
        print("[DEBUG] proposal_engine.py started.")
        print(f"[MEMORY PROFILE] 7. Before PDF generation: {get_memory_usage():.2f} MB")
        print(f"[DEBUG] PDF generation started. Saving file to path: {pdf_path}")
        generate_pdf_from_data(merged_data, output_path=pdf_path)
        print(f"[MEMORY PROFILE] 9. After PDF generation completes: {get_memory_usage():.2f} MB")
        print(f"[DEBUG] PDF generation completed. Output file: {pdf_filename}")
        print("[DEBUG] PDF generated successfully.")
        
        # Clean up source Excel file from uploads/
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
                print(f"[DEBUG] Deleted temporary excel source: {filepath}")
        except Exception as err:
            print(f"[DEBUG WARN] Failed to delete temporary source file: {str(err)}")
            
        print("[DEBUG] Flask API: Returning success response with PDF download URL.")
        print("[DEBUG] ==================================================\n")
        print(f"[MEMORY PROFILE] 10. Before returning the response: {get_memory_usage():.2f} MB")
        return jsonify({
            "status": "success",
            "pdf_url": f"/api/download_pdf?file={pdf_filename}"
        })
    except ValueError as ve:
        print(f"[DEBUG ERROR] Validation failed: {str(ve)}")
        print("[DEBUG] ==================================================\n")
        print(f"[MEMORY PROFILE] 10. Before returning the response (error): {get_memory_usage():.2f} MB")
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"[DEBUG ERROR] Exception occurred during proposal generation: {str(e)}")
        traceback.print_exc()
        print(f"[TRACEBACK]\n{traceback.format_exc()}")
 
        print("[DEBUG] ==================================================\n")
        print(f"[MEMORY PROFILE] 10. Before returning the response (exception): {get_memory_usage():.2f} MB")
        return jsonify({"error": f"Failed to generate proposal PDF: {str(e)}"}), 500

@app.route("/api/download_pdf", methods=["GET"])
def download_pdf():
    """Serves the generated PDF file from uploads/ as an attachment."""
    filename = request.args.get("file")
    if not filename:
        return jsonify({"error": "Missing 'file' parameter"}), 400
        
    filepath = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        print(f"[DEBUG] Serving file attachment: {filepath}")
        print("[DEBUG] send_file() executed.")
        return send_file(
            filepath,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    else:
        print(f"[DEBUG ERROR] PDF file not found: {filepath}")
        return jsonify({"error": "PDF file not found or has expired."}), 404

@app.route("/api/default_data", methods=["GET"])
def get_default_data():
    """Copies CLIENT_TEMPLATE.xlsx or PORTFOLIO_REVIEW_TEMPLATE.xlsx to uploads/ and returns parsed info."""
    workflow = request.args.get("workflow", "recommendation")
    print(f"[DEBUG] Copying default template for workflow '{workflow}' to uploads/ directory")
    
    if workflow == "review":
        review_template_path = "PORTFOLIO_REVIEW_TEMPLATE.xlsx"
        if os.path.exists(review_template_path):
            try:
                unique_filename = f"{int(time.time())}_demo_{uuid.uuid4().hex[:4]}_PORTFOLIO_REVIEW_TEMPLATE.xlsx"
                filepath = os.path.join(UPLOADS_DIR, unique_filename)
                shutil.copy(review_template_path, filepath)
                
                from review_engine import parse_review_excel
                parsed_data = parse_review_excel(filepath)
                
                client_name = parsed_data["client"].get("client_name", "Mrs. Anu Shivdasani & Family")
                portfolio_corpus = parsed_data["client"].get("portfolio_value_inr", 0.0)
                
                holdings_list = []
                for h in parsed_data.get("holdings", []):
                    holdings_list.append({
                        "name": h.get("product_name", "Unnamed Holding"),
                        "class": h.get("asset_class", "Mutual Fund"),
                        "allocation_pct": h.get("allocation_pct", 0.0),
                        "gain_loss_pct": h.get("gain_loss_pct", 0.0)
                    })
                    
                return jsonify({
                    "status": "success",
                    "workflow": "review",
                    "client_name": client_name,
                    "corpus": f"{int(portfolio_corpus):,}" if portfolio_corpus > 0.0 else "0",
                    "funds": holdings_list,
                    "analytics": parsed_data.get("analytics"),
                    "filepath": filepath,
                    "proposal_data": parsed_data,
                    "message": "Demo PORTFOLIO_REVIEW_TEMPLATE.xlsx loaded successfully!"
                })
            except Exception as e:
                traceback.print_exc()
                print(f"[TRACEBACK]\n{traceback.format_exc()}")
                return jsonify({"error": f"Failed to copy default template: {str(e)}"}), 500

        else:
            return jsonify({"error": "Default PORTFOLIO_REVIEW_TEMPLATE.xlsx not found in workspace"}), 404
            
    if os.path.exists(DEFAULT_EXCEL_PATH):
        try:
            unique_filename = f"{int(time.time())}_demo_{uuid.uuid4().hex[:4]}_CLIENT_TEMPLATE.xlsx"
            filepath = os.path.join(UPLOADS_DIR, unique_filename)
            shutil.copy(DEFAULT_EXCEL_PATH, filepath)
            
            # Use intelligent parser
            parsed_data = parse_messy_excel(filepath)
            client_name = parsed_data["client"].get("Client Name", "Mrs. Anu Shivdasani & Family")
            portfolio_corpus = parsed_data["client"].get("Portfolio Corpus (INR)", "10,00,00,000")
            
            funds_list = []
            for p in parsed_data.get("products", []):
                funds_list.append({
                    "name": p.get("Product Name", "Unnamed Product"),
                    "class": p.get("Asset Class", "Mutual Fund")
                })
                
            return jsonify({
                "status": "success",
                "client_name": client_name,
                "corpus": portfolio_corpus,
                "sheets": parsed_data["sheets"],
                "allocation_columns": parsed_data["allocation_columns"],
                "products_columns": parsed_data["products_columns"],
                "funds": funds_list,
                "missing_fields": parsed_data["missing_fields"],
                "filepath": filepath,
                "proposal_data": parsed_data,
                "message": "Demo CLIENT_TEMPLATE.xlsx loaded successfully!"
            })
        except Exception as e:
            traceback.print_exc()
            print(f"[TRACEBACK]\n{traceback.format_exc()}")
            return jsonify({"error": f"Failed to copy default template: {str(e)}"}), 500

    else:
        return jsonify({"error": "Default CLIENT_TEMPLATE.xlsx not found in workspace"}), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
