import os
import json
import traceback
import re
import pandas as pd

# Column Aliases for Mapping
ALLOC_COLUMN_ALIASES = {
    "Part": ["part", "part no", "segment part"],
    "Segment Name": ["segment name", "segment", "category", "asset class", "portfolio segment", "asset class name", "segment description"],
    "Allocation %": ["allocation %", "allocation", "weight", "%", "alloc %", "percentage", "share", "weight (%)", "allocation (%)", "alloc (%)", "portfolio weight"],
    "Objective": ["objective", "goal", "purpose", "target", "description", "strategic role", "role & objective"]
}

PRODUCT_COLUMN_ALIASES = {
    "Part": ["part", "part no", "segment part"],
    "Segment": ["segment", "category", "segment name", "type", "asset type", "asset class", "class", "portfolio segment"],
    "Product Name": ["product name", "product", "fund name", "fund", "scheme", "scheme name", "investment name", "investment", "portfolio holdings", "holdings", "security", "security name", "particulars", "description", "recommended product", "recommended products", "recommended fund", "recommended funds", "name of product", "name of scheme", "asset classwise recommendation", "mutual funds", "aif recommendation", "portfolio asset class", "proposed portfolio", "assets", "name of the fund", "name of the scheme", "fund name / scheme name"],
    "Asset Class": ["asset class", "class", "type", "asset type", "instrument"],
    "Allocation (INR)": ["allocation (inr)", "allocation", "amount", "corpus", "inr", "allocated amount", "value", "amt", "invested amount", "investment amount", "invested", "value (inr)", "invested amt", "current value", "market value", "holding value", "allocation (rs.)", "allocation (rs)", "allocation rs", "allocation lakhs", "allocation in lakhs", "allocation (in cr)", "allocation (cr)", "value in rs", "invested value", "proposed allocation", "rupees", "rs.", "rs", "lumpsum", "lump sum", "lump-sum", "lumpsum amount", "lumpsum investment"],
    "SIP Amount": ["sip", "sip amount", "sip (inr)", "sip (rs.)", "sip (rs)", "sip rs", "sip amount (inr)", "sip amount (rs)", "monthly sip", "monthly sip amount", "sip (monthly)", "sip amt"],
    "Target Return": ["target return", "return", "cagr", "yield", "irr", "expected return", "expected returns", "expected cagr", "target cagr", "net irr", "returns", "expected cagr (%)", "returns (%)", "return (%)", "cagr (%)", "expected return (%)", "yield (%)", "target returns", "irr (%)", "yield p.a.", "cagr p.a."],
    "Investment Horizon": ["horizon", "term", "duration", "tenure", "period", "time horizon", "investment horizon"],
    "Core Rationale": ["core rationale", "rationale", "reason", "description", "details", "why selected", "commentary", "remarks", "comments", "notes", "analysis", "rationale / description", "investment rationale", "why chosen", "recommendation rationale"]
}

FIRM_KEYS = {
    "Firm Name": ["firm name", "company name", "wealth name", "organization"],
    "Tagline": ["tagline", "motto", "philosophy"],
    "AMFI ARN": ["arn", "amfi arn", "registration", "arn code"],
    "Email": ["email", "e-mail", "mail", "contact email"],
    "Website": ["website", "web", "site", "url"],
    "Phone": ["phone", "contact", "mobile", "tel", "telephone"],
    "Address": ["address", "office", "location", "corporate address"],
    "Advisor Name": ["advisor name", "advisor", "representative", "wealth advisor"],
    "Advisor Title": ["advisor title", "designation", "title", "role"],
    "Advisor Credentials": ["credentials", "qualification", "degree"],
    "Advisor Background": ["background", "experience", "past experience"]
}

CLIENT_KEYS = {
    "Client Name": ["client name", "client", "family name", "investor", "investor name", "client name (family name)", "name", "prepared for", "proposal for", "client info"],
    "Portfolio Corpus (INR)": ["portfolio corpus", "corpus", "investment corpus", "total corpus", "total capital", "portfolio value", "corpus value", "total portfolio", "corpus (inr)", "total investment", "proposed investment"],
    "Report Date": ["report date", "date", "proposal date", "month"],
    "Investment Horizon": ["investment horizon", "horizon", "term", "duration", "time horizon", "tenor", "period", "horizon (years)"],
    "Risk Profile": ["risk profile", "risk", "risk capacity", "risk assessment", "risk tolerance", "profile"],
    "Primary Objective": ["primary objective", "objective", "goal", "objectives", "target", "goals", "portfolio objective"],
    "Tax Bracket": ["tax bracket", "tax", "tax rate", "tax bracket %"]
}

def _classify_fund(product_name, category_or_class):
    name = str(product_name).lower()
    cat = str(category_or_class).lower()
    
    is_pms = (
        "pms" in cat or "pms" in name or 
        "portfolio management" in cat or "portfolio management" in name or 
        "p.m.s" in cat or "p.m.s" in name or
        any(kw in name for kw in ["buoyant", "rising stars", "valuequest", "ask growth", "marcellus"])
    )
    if is_pms:
        return 4, "Portfolio Management Services (PMS)", "15% - 18%"

    if "liquid" in name or "liquid" in cat:
        return 1, "Liquid Fund", "6% - 8%"
    elif "arbitrage" in name or "arbitrage" in cat:
        return 1, "Arbitrage Fund", "6% - 8%"
    elif "corporate bond" in name or "corporate bond" in cat:
        return 2, "Corporate Bond Fund", "7.5% - 8.5%"
    elif "credit risk" in name or "credit risk" in cat:
        return 2, "Credit Risk Fund", "8% - 9%"
    elif "banking and psu" in name or "banking & psu" in name or "banking and psu" in cat or "banking & psu" in cat:
        return 2, "Banking and PSU Fund", "7.5% - 8.5%"
    elif "dynamic bond" in name or "dynamic bond" in cat:
        return 2, "Dynamic Bond Fund", "7.5% - 8.5%"
    elif "gilt" in name or "gilt" in cat:
        return 2, "Gilt Fund", "7% - 8%"
    elif "low duration" in name or "low duration" in cat:
        return 2, "Low Duration Fund", "7% - 8%"
    elif "money market" in name or "money market" in cat:
        return 1, "Money Market Fund", "6.5% - 7.5%"
    elif "overnight" in name or "overnight" in cat:
        return 1, "Overnight Fund", "6% - 7%"
    elif "short duration" in name or "short duration" in cat:
        return 2, "Short Duration Fund", "7% - 8%"
    elif "ultra short" in name or "ultra short" in cat:
        return 1, "Ultra Short Duration Fund", "6.5% - 7.5%"
    elif "medium duration" in name or "medium duration" in cat:
        return 2, "Medium Duration Fund", "7.5% - 8.5%"
    elif "floater" in name or "floater" in cat:
        return 2, "Floater Fund", "7.5% - 8.5%"
    elif "balanced advantage" in name or "baf" in name or "dynamic asset allocation" in name or "dynamic equity" in name or "balanced advantage" in cat or "dynamic asset allocation" in cat:
        return 3, "Balanced Advantage Fund", "10% - 12%"
    elif "equity hybrid" in name or "aggressive hybrid" in name or "equity hybrid" in cat or "aggressive hybrid" in cat:
        return 3, "Aggressive Hybrid Fund", "11% - 13%"
    elif "debt hybrid" in name or "conservative hybrid" in name or "debt hybrid" in cat or "conservative hybrid" in cat:
        return 2, "Conservative Hybrid Fund", "8% - 9%"
    elif "multi asset" in name or "multi-asset" in name or "multiasset" in name or "multi asset" in cat:
        return 3, "Multi Asset Allocation Fund", "11% - 13%"
    elif "small cap" in name or "small-cap" in name or "smallcap" in name or "small cap" in cat or "smallcap" in cat:
        return 4, "Small Cap Fund", "16% - 18%"
    elif "mid cap" in name or "mid-cap" in name or "midcap" in name or "mid cap" in cat or "midcap" in cat:
        return 4, "Mid Cap Fund", "14% - 16%"
    elif "large & mid" in name or "large and mid" in name or "large-and-mid" in name or "large & mid" in cat:
        return 4, "Large & Mid Cap Fund", "13% - 15%"
    elif "large cap" in name or "large-cap" in name or "largecap" in name or "large cap" in cat or "largecap" in cat:
        return 4, "Large Cap Fund", "12% - 14%"
    elif "flexi cap" in name or "flexicap" in name or "flexi-cap" in name or "flexi cap" in cat or "flexicap" in cat:
        return 4, "Flexi Cap Fund", "14% - 16%"
    elif "multi cap" in name or "multicap" in name or "multi-cap" in name or "multi cap" in cat or "multicap" in cat:
        return 4, "Multi Cap Fund", "14% - 16%"
    
    # Generic fallback
    if "hybrid" in name or "hybrid" in cat:
        return 3, "Aggressive Hybrid Fund", "11% - 13%"
    elif "debt" in name or "debt" in cat or "bond" in name:
        return 2, "Corporate Bond Fund", "7.5% - 8.5%"
    elif "equity" in name or "equity" in cat:
        return 4, "Flexi Cap Fund", "14% - 16%"
        
    return 4, "Flexi Cap Fund", "14% - 16%"

def clean_float_val(val):
    if val is None:
        return 0.0
    val_str = str(val).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace(" ", "").strip()
    if not val_str or val_str == "nan":
        return 0.0
        
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1].strip()
        
    multiplier = 1.0
    if "crore" in val_str or "cr" in val_str:
        multiplier = 10000000.0
        val_str = val_str.replace("crores", "").replace("crore", "").replace("cr", "")
    elif "lakh" in val_str or "l" in val_str:
        if any(x in val_str for x in ["lakhs", "lakh"]):
            multiplier = 100000.0
            val_str = val_str.replace("lakhs", "").replace("lakh", "")
        elif val_str.endswith("l"):
            multiplier = 100000.0
            val_str = val_str[:-1]
    elif "million" in val_str or val_str.endswith("m"):
        multiplier = 1000000.0
        val_str = val_str.replace("million", "")
        if val_str.endswith("m"):
            val_str = val_str[:-1]
    elif "thousand" in val_str or val_str.endswith("k"):
        multiplier = 1000.0
        val_str = val_str.replace("thousand", "")
        if val_str.endswith("k"):
            val_str = val_str[:-1]
            
    try:
        val_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not val_str:
            return 0.0
        result = float(val_str) * multiplier
        if is_negative:
            result = -result
        return result
    except ValueError:
        return 0.0

def clean_product_name(name):
    if not name:
        return ""
    name_str = str(name).strip()
    # Correct Smallcao to Smallcap
    name_str = re.sub(r"\bsmallcao\b", "Smallcap", name_str, flags=re.IGNORECASE)
    # Correct Sunlife to Sun Life
    name_str = re.sub(r"\bSunlife\b", "Sun Life", name_str, flags=re.IGNORECASE)
    # Capitalize fund/fof properly
    name_str = re.sub(r"\bfund\b", "Fund", name_str, flags=re.IGNORECASE)
    name_str = re.sub(r"\bfof\b", "FoF", name_str, flags=re.IGNORECASE)
    return name_str

def alias_matches_value(alias, cell_value):
    alias_clean = alias.strip().lower()
    val_clean = str(cell_value).strip().lower()
    if not val_clean or not alias_clean:
        return False
    if alias_clean.isalnum() and len(alias_clean) <= 3:
        pattern = rf"\b{re.escape(alias_clean)}\b"
        return bool(re.search(pattern, val_clean))
    else:
        return alias_clean in val_clean

def _scan_for_products_table(df):
    df = df.fillna("")
    best_row_idx = None
    best_matches = 0
    best_mapped_columns = {}
    
    # 1. Standard Header Row Scan (up to 100 rows)
    for r_idx in range(min(df.shape[0], 100)):
        row_vals = [str(x).strip().lower() for x in df.iloc[r_idx, :].values]
        matches = 0
        current_mapped = {}
        for c_idx, val in enumerate(row_vals):
            if not val:
                continue
            for target_col, aliases in PRODUCT_COLUMN_ALIASES.items():
                if target_col in current_mapped.values():
                    continue
                if any(alias_matches_value(a, val) for a in aliases):
                    current_mapped[c_idx] = target_col
                    matches += 1
                    break
                    
        # Check that we have mapped at least the critical columns (Product Name and either Lumpsum Allocation or SIP Amount)
        if matches > best_matches and any(x in current_mapped.values() for x in ["Product Name"]) and any(x in current_mapped.values() for x in ["Allocation (INR)", "SIP Amount"]):
            best_matches = matches
            best_row_idx = r_idx
            best_mapped_columns = current_mapped
            
    # 2. Fallback content analysis if header scan failed or was incomplete
    if best_row_idx is None or best_matches < 2:
        print("[Parser Heuristic] Standard product header scan failed. Running fallback column content analysis...")
        name_col = None
        alloc_col = None
        rationale_col = None
        return_col = None
        
        nr, nc = df.shape
        for c_idx in range(nc):
            col_vals = df.iloc[:, c_idx].dropna().astype(str).tolist()
            fund_score = 0
            amount_score = 0
            cagr_score = 0
            rationale_score = 0
            
            for val in col_vals:
                val_clean = val.strip()
                if not val_clean or val_clean.lower() == "nan":
                    continue
                val_lower = val_clean.lower()
                
                # Fund score
                if any(kw in val_lower for kw in ["fund", "pms", "aif", "equity", "debt", "hybrid", "gold", "silver", "index", "baf", "savings", "arbitrage", "liquid"]):
                    fund_score += 1
                
                # Amount score
                num_val = clean_float_val(val_clean)
                if num_val > 5000:
                    amount_score += 1
                    
                # CAGR score
                if "%" in val_clean and any(kw in val_lower for kw in ["return", "cagr", "yield", "irr", "expected"]):
                    cagr_score += 1
                elif any(kw in val_lower for kw in ["cagr", "yield", "irr"]):
                    cagr_score += 1
                    
                # Rationale score
                if len(val_clean) > 40 and " " in val_clean:
                    rationale_score += 1
            
            total_non_empty = sum(1 for val in col_vals if val.strip() and val.strip().lower() != "nan")
            if total_non_empty > 0:
                if fund_score > total_non_empty * 0.15 and name_col is None:
                    name_col = c_idx
                elif amount_score > total_non_empty * 0.15 and alloc_col is None:
                    alloc_col = c_idx
                elif rationale_score > total_non_empty * 0.15 and rationale_col is None:
                    rationale_col = c_idx
                elif cagr_score > total_non_empty * 0.15 and return_col is None:
                    return_col = c_idx
                    
        if name_col is not None and alloc_col is not None:
            best_row_idx = -1
            for r_idx in range(min(nr, 15)):
                val1 = str(df.iloc[r_idx, name_col]).strip().lower()
                val2 = str(df.iloc[r_idx, alloc_col]).strip().lower()
                if val1 and val2 and val1 != "nan" and val2 != "nan":
                    best_row_idx = r_idx
                    break
            
            best_mapped_columns = {
                name_col: "Product Name",
                alloc_col: "Allocation (INR)"
            }
            if rationale_col is not None:
                best_mapped_columns[rationale_col] = "Core Rationale"
            if return_col is not None:
                best_mapped_columns[return_col] = "Target Return"
            best_matches = len(best_mapped_columns)
            print(f"[Parser Heuristic] Fallback column mapping succeeded: Row={best_row_idx}, Name={name_col}, Alloc={alloc_col}")

    # 3. Product Extraction from identified headers
    if best_row_idx is not None and best_matches >= 2:
        products_list = []
        consecutive_empty = 0
        for r_idx in range(best_row_idx + 1, df.shape[0]):
            row_vals_lower = [str(x).strip().lower() for x in df.iloc[r_idx, :].values]
            if any("total" in val or "sum" in val or "overall" in val for val in row_vals_lower if val):
                print(f"[Parser] Encountered 'total' row at row index {r_idx}. Stopping product table extraction.")
                break
                
            row_data = {}
            row_empty = True
            for c_idx, target_col in best_mapped_columns.items():
                val = str(df.iloc[r_idx, c_idx]).strip()
                if val and val.lower() != "nan" and val != "":
                    row_empty = False
                row_data[target_col] = val
                
            if row_empty:
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    break
                continue
                
            consecutive_empty = 0
            
            prod_name = row_data.get("Product Name", "").strip()
            alloc_val = clean_float_val(row_data.get("Allocation (INR)", "0"))
            sip_val = clean_float_val(row_data.get("SIP Amount", "0"))
            horizon_val = row_data.get("Investment Horizon", "").strip()
            
            if not prod_name and alloc_val == 0.0 and sip_val == 0.0:
                continue
                
            if not prod_name:
                prod_name = f"Strategic Holding {len(products_list) + 1}"
                row_data["Product Name"] = prod_name
            else:
                row_data["Product Name"] = clean_product_name(prod_name)
                
            row_data["Allocation (INR)"] = alloc_val
            row_data["SIP Amount"] = sip_val
            row_data["Investment Horizon"] = horizon_val
            
            products_list.append(row_data)
            
        return products_list, best_row_idx, list(best_mapped_columns.values())
        
    return None, None, None

def _scan_for_allocation_table(df):
    df = df.fillna("")
    best_row_idx = None
    best_matches = 0
    best_mapped_columns = {}
    
    # 1. Standard Header Row Scan (up to 100 rows)
    for r_idx in range(min(df.shape[0], 100)):
        row_vals = [str(x).strip().lower() for x in df.iloc[r_idx, :].values]
        matches = 0
        current_mapped = {}
        for c_idx, val in enumerate(row_vals):
            if not val:
                continue
            for target_col, aliases in ALLOC_COLUMN_ALIASES.items():
                if target_col in current_mapped.values():
                    continue
                if any(alias_matches_value(a, val) for a in aliases):
                    current_mapped[c_idx] = target_col
                    matches += 1
                    break
                    
        if matches > best_matches and any(x in current_mapped.values() for x in ["Segment Name"]) and any(x in current_mapped.values() for x in ["Allocation %"]):
            best_matches = matches
            best_row_idx = r_idx
            best_mapped_columns = current_mapped
            
    # 2. Fallback content analysis for allocation
    if best_row_idx is None or best_matches < 2:
        print("[Parser Heuristic] Standard allocation header scan failed. Running fallback column content analysis...")
        seg_col = None
        pct_col = None
        
        nr, nc = df.shape
        for c_idx in range(nc):
            col_vals = df.iloc[:, c_idx].dropna().astype(str).tolist()
            seg_score = 0
            pct_score = 0
            
            for val in col_vals:
                val_clean = val.strip()
                if not val_clean or val_clean.lower() == "nan":
                    continue
                val_lower = val_clean.lower()
                
                # Segment score
                if any(kw in val_lower for kw in ["liquidity", "hybrid", "multi-asset", "multi asset", "equity compounding", "concentrated growth", "safety & stability", "yield enhancement", "regular income", "hedged growth", "wealth growth", "wealth creation", "stable income"]):
                    seg_score += 1
                
                # Percentage score
                if "%" in val_clean:
                    pct_score += 1
                else:
                    f_val = clean_float_val(val_clean)
                    if 0.0 < f_val <= 1.0:
                        pct_score += 1
                        
            total_non_empty = sum(1 for val in col_vals if val.strip() and val.strip().lower() != "nan")
            if total_non_empty > 0:
                if seg_score > total_non_empty * 0.15 and seg_col is None:
                    seg_col = c_idx
                elif pct_score > total_non_empty * 0.15 and pct_col is None:
                    pct_col = c_idx
                    
        if seg_col is not None and pct_col is not None:
            best_row_idx = -1
            for r_idx in range(min(nr, 15)):
                val1 = str(df.iloc[r_idx, seg_col]).strip().lower()
                val2 = str(df.iloc[r_idx, pct_col]).strip().lower()
                if val1 and val2 and val1 != "nan" and val2 != "nan":
                    best_row_idx = r_idx
                    break
            best_mapped_columns = {
                seg_col: "Segment Name",
                pct_col: "Allocation %"
            }
            # Look for objective column
            for c_idx in range(nc):
                if c_idx != seg_col and c_idx != pct_col:
                    col_vals = df.iloc[:, c_idx].dropna().astype(str).tolist()
                    long_strings = sum(1 for val in col_vals if len(val.strip()) > 30 and " " in val.strip())
                    if long_strings > len(col_vals) * 0.15:
                        best_mapped_columns[c_idx] = "Objective"
                        break
            best_matches = len(best_mapped_columns)
            print(f"[Parser Heuristic] Fallback allocation mapping succeeded: Row={best_row_idx}, Seg={seg_col}, Pct={pct_col}")

    # 3. Extraction
    if best_row_idx is not None and best_matches >= 2:
        alloc_list = []
        consecutive_empty = 0
        for r_idx in range(best_row_idx + 1, df.shape[0]):
            row_vals_lower = [str(x).strip().lower() for x in df.iloc[r_idx, :].values]
            if any("total" in val or "sum" in val or "overall" in val for val in row_vals_lower if val):
                break
            row_data = {}
            row_empty = True
            for c_idx, target_col in best_mapped_columns.items():
                val = str(df.iloc[r_idx, c_idx]).strip()
                if val and val.lower() != "nan" and val != "":
                    row_empty = False
                row_data[target_col] = val
                
            if row_empty:
                consecutive_empty += 1
                if consecutive_empty >= 5:
                    break
                continue
                
            consecutive_empty = 0
            if row_data.get("Segment Name"):
                alloc_val = clean_float_val(row_data.get("Allocation %", "0"))
                row_data["Allocation %"] = alloc_val
                alloc_list.append(row_data)
        return alloc_list, best_row_idx, list(best_mapped_columns.values())
        
    return None, None, None

def _extract_all_key_values(xl, keys_map):
    found = {}
    
    # Sort aliases by length descending
    sorted_keys_map = {}
    for target_key, aliases in keys_map.items():
        all_aliases = list(set([target_key] + aliases))
        sorted_keys_map[target_key] = sorted(all_aliases, key=len, reverse=True)
        
    # Pre-calculate normalized aliases
    normalized_keys = {}
    for target_key, aliases in sorted_keys_map.items():
        normalized_keys[target_key] = [re.sub(r'[^a-z0-9]', '', str(a).lower()) for a in aliases]
        
    def extract_from_cell_prefix(val_str, alias):
        alias_lower = alias.lower()
        val_lower = val_str.lower()
        
        # Match with normalized spaces
        val_clean = re.sub(r'[^a-z0-9]', ' ', val_lower)
        alias_clean = re.sub(r'[^a-z0-9]', ' ', alias_lower)
        
        val_clean = re.sub(r'\s+', ' ', val_clean).strip()
        alias_clean = re.sub(r'\s+', ' ', alias_clean).strip()
        
        if val_clean.startswith(alias_clean):
            rem_idx = len(alias_clean)
            if rem_idx < len(val_clean):
                next_char = val_clean[rem_idx]
                if next_char == ' ':
                    alnum_count = sum(1 for c in alias_clean if c.isalnum())
                    orig_idx = 0
                    seen_alnum = 0
                    for i, c in enumerate(val_str):
                        if c.isalnum():
                            seen_alnum += 1
                        if seen_alnum == alnum_count:
                            orig_idx = i + 1
                            break
                    rem = val_str[orig_idx:].strip()
                    rem_clean = rem.lstrip(":-= ")
                    return rem_clean
            elif rem_idx == len(val_clean):
                return ""
        return ""

    for sheet_name, df in xl.items():
        df = df.fillna("")
        nr, nc = df.shape
        for r_idx in range(nr):
            for c_idx in range(nc):
                val_str = str(df.iloc[r_idx, c_idx]).strip()
                if not val_str or val_str.lower() == "nan":
                    continue
                
                val_norm = re.sub(r'[^a-z0-9]', '', val_str.lower())
                if not val_norm:
                    continue
                    
                for target_key in sorted_keys_map:
                    if target_key in found:
                        continue
                        
                    matched = False
                    extracted_val = ""
                    
                    # 1. Check exact normalized match first
                    for idx, norm_a in enumerate(normalized_keys[target_key]):
                        if val_norm == norm_a:
                            # Extract from adjacent cell
                            for next_c in range(c_idx + 1, nc):
                                candidate = str(df.iloc[r_idx, next_c]).strip()
                                if candidate and candidate.lower() != "nan" and candidate != "":
                                    extracted_val = candidate
                                    matched = True
                                    break
                            if not matched:
                                for next_r in range(r_idx + 1, nr):
                                    candidate = str(df.iloc[next_r, c_idx]).strip()
                                    if candidate and candidate.lower() != "nan" and candidate != "":
                                        extracted_val = candidate
                                        matched = True
                                        break
                            if matched:
                                break
                                
                    # 2. Check prefix matches only if not matched exactly
                    if not matched:
                        for alias in sorted_keys_map[target_key]:
                            res = extract_from_cell_prefix(val_str, alias)
                            if res and res.lower() != "nan" and res != "":
                                extracted_val = res
                                matched = True
                                break
                                
                    if matched and extracted_val:
                        found[target_key] = extracted_val
                        break
                        
    return found

def parse_messy_excel(filepath, api_key=None):
    """
    Parses messy Excel files dynamically, supporting sheet-independent layout checks,
    multiple sheets or single-sheet portfolios, semantic key extraction and fallback heuristics.
    """
    print(f"[Parser] Commencing intelligent parsing of: {filepath}")
    try:
        xl = pd.read_excel(filepath, sheet_name=None, header=None)
    except Exception as e:
        print(f"[Parser ERROR] Failed reading Excel: {str(e)}")
        raise ValueError(f"Corrupted or invalid Excel spreadsheet: {str(e)}")

    # Scan all sheets and cell values for SWP presence
    import re
    has_swp = False
    for sheet_name in xl.keys():
        sheet_lower = sheet_name.lower()
        if re.search(r'\bswp\b', sheet_lower) or "systematic withdrawal" in sheet_lower:
            has_swp = True
            break
    if not has_swp:
        for sheet_name, df in xl.items():
            df_str = df.astype(str).values
            for row in df_str:
                for cell in row:
                    cell_lower = str(cell).lower()
                    if re.search(r'\bswp\b', cell_lower) or "systematic withdrawal" in cell_lower:
                        has_swp = True
                        break
                if has_swp:
                    break
            if has_swp:
                break
    print(f"[Parser] SWP keyword detected: {has_swp}")

    # Default mappings structure
    firm_info = {
        "Firm Name": "Samarth Wealth Pvt. Ltd.",
        "Tagline": "Clients First. Always and Everytime",
        "Founded": "2011",
        "Team Size": "30",
        "AUM (Crores)" : "1500",
        "Location": "Thane, Maharashtra",
        "Address": "G-75/76, Eternity Commercial Premises, Off LBS Marg, Thane (W) - 400604",
        "Email": "relationships@samarthedufin.com",
        "Website": "www.samarthwealth.in",
        "Phone": "+91 7738245239",
        "AMFI ARN": "ARN-286847",
        "Advisor Name": "Abhinandan Honale",
        "Advisor Title": "Co-Founder",
        "Advisor Credentials": "FRM, MBA Finance"
    }

    client_info = {
        "Client Name": "",
        "Portfolio Corpus (INR)": "",
        "Report Date": "May 2026",
        "Investment Horizon": "5+ Years",
        "Risk Profile": "Moderate-Aggressive",
        "Primary Objective": "Wealth Compounding",
        "Tax Bracket": "30%"
    }

    allocation_list = []
    products_list = []
    
    products_sheet_name = None
    products_header_idx = None
    products_cols = []
    
    sheet_names = list(xl.keys())
    
    def product_sheet_priority(name):
        n_low = name.lower()
        if "product" in n_low or "holding" in n_low or "portfolio" in n_low or "recommendation" in n_low:
            return 0
        if "client" in n_low or "info" in n_low or "summary" in n_low or "proposal" in n_low:
            return 1
        if "sheet1" in n_low:
            return 2
        return 3
        
    sorted_product_sheets = sorted(sheet_names, key=product_sheet_priority)
    
    # Scan for products table
    for sheet_name in sorted_product_sheets:
        df = xl[sheet_name]
        p_list, h_idx, p_cols = _scan_for_products_table(df)
        if p_list and len(p_list) > 0:
            products_sheet_name = sheet_name
            products_list = p_list
            products_header_idx = h_idx
            products_cols = p_cols
            print(f"[Parser] Successfully detected Products table in sheet '{sheet_name}' at row {h_idx}.")
            break

    # Scan for asset allocation table (if separate)
    def alloc_sheet_priority(name):
        n_low = name.lower()
        if "allocation" in n_low or "asset" in n_low or "dashboard" in n_low:
            return 0
        if "summary" in n_low:
            return 1
        if "sheet1" in n_low:
            return 2
        return 3
        
    sorted_alloc_sheets = sorted(sheet_names, key=alloc_sheet_priority)
    
    allocation_sheet_name = None
    allocation_cols = []
    for sheet_name in sorted_alloc_sheets:
        if sheet_name == products_sheet_name and len(xl) > 1:
            continue
        df = xl[sheet_name]
        a_list, h_idx, a_cols = _scan_for_allocation_table(df)
        if a_list and len(a_list) > 0:
            allocation_sheet_name = sheet_name
            allocation_list = a_list
            allocation_cols = a_cols
            print(f"[Parser] Successfully detected Asset Allocation table in sheet '{sheet_name}' at row {h_idx}.")
            break

    # 3. Scan all cells for key-value fields
    client_kv = _extract_all_key_values(xl, CLIENT_KEYS)
    if "Portfolio Corpus (INR)" in client_kv:
        val_cleaned = clean_float_val(client_kv["Portfolio Corpus (INR)"])
        if val_cleaned > 0:
            client_info["Portfolio Corpus (INR)"] = f"{int(val_cleaned):,}"
        else:
            print(f"[Parser] Discarding non-numeric corpus value match: '{client_kv['Portfolio Corpus (INR)']}'")
            if "Portfolio Corpus (INR)" in client_info:
                del client_info["Portfolio Corpus (INR)"]
            
    for k, v in client_kv.items():
        if k != "Portfolio Corpus (INR)":
            client_info[k] = v
    
    firm_kv = _extract_all_key_values(xl, FIRM_KEYS)
    firm_info.update(firm_kv)

    # 4. Fallback Heuristics for Client Info
    if not client_info.get("Client Name"):
        if products_sheet_name and products_header_idx is not None:
            df_prod = xl[products_sheet_name]
            candidates = []
            for r in range(min(products_header_idx, df_prod.shape[0])):
                for c in range(df_prod.shape[1]):
                    val = str(df_prod.iloc[r, c]).strip()
                    if val and val.lower() != "nan" and len(val) > 2:
                        candidates.append(val)
            
            client_candidate = None
            firm_candidate = None
            for cand in candidates:
                cand_lower = cand.lower()
                if any(kw in cand_lower for kw in ["wealth", "advisory", "advisors", "capital", "securities", "pvt", "ltd", "firm", "company"]):
                    if not firm_candidate:
                        firm_candidate = cand
                else:
                    if not client_candidate:
                        client_candidate = cand
            
            if client_candidate:
                client_info["Client Name"] = client_candidate
                print(f"[Parser Heuristic] Deduced Client Name: {client_candidate}")
            if firm_candidate:
                firm_info["Firm Name"] = firm_candidate
                print(f"[Parser Heuristic] Deduced Firm Name: {firm_candidate}")

    # 5. Dynamic Product Classification and Part allocation
    for p in products_list:
        part_val = p.get("Part")
        part_num = None
        if part_val:
            try:
                nums = re.findall(r'\d+', str(part_val))
                if nums:
                    part_num = int(nums[0])
            except:
                pass
                
        cat_class = p.get("Segment") or p.get("Asset Class") or p.get("Category") or ""
        
        if part_num not in [1, 2, 3, 4]:
            part, segment, _ = _classify_fund(p.get("Product Name", ""), cat_class)
            p["Part"] = part
            p["Segment"] = segment
        else:
            p["Part"] = part_num
            if not p.get("Segment"):
                segment_names = {
                    1: "Liquid Fund",
                    2: "Corporate Bond Fund",
                    3: "Multi Asset Allocation Fund",
                    4: "Flexi Cap Fund"
                }
                p["Segment"] = segment_names.get(part_num, "Flexi Cap Fund")

    # 6. Deduce Portfolio Corpus from product list sums if missing or mismatched
    total_amt = sum(clean_float_val(p.get("Allocation (INR)", "0")) for p in products_list)
    if not client_info.get("Portfolio Corpus (INR)"):
        if total_amt > 0:
            client_info["Portfolio Corpus (INR)"] = f"{int(total_amt):,}"
            print(f"[Parser Heuristic] Deduced Portfolio Corpus from products: {client_info['Portfolio Corpus (INR)']}")
    else:
        extracted_val = clean_float_val(client_info.get("Portfolio Corpus (INR)", "0"))
        if extracted_val > 0 and abs(extracted_val - total_amt) > 1.0:
            print(f"[Parser Heuristic] Stated corpus {extracted_val} differs from allocations sum {total_amt}. Aligning to {total_amt}.")
            client_info["Portfolio Corpus (INR)"] = f"{int(total_amt):,}"

    # 7. Normalize asset allocation percentages
    if allocation_list:
        total_pct = sum(clean_float_val(a.get("Allocation %", 0)) for a in allocation_list)
        if 0.99 <= total_pct <= 1.01:
            for a in allocation_list:
                a["Allocation %"] = round(clean_float_val(a.get("Allocation %", 0)) * 100)
    else:
        print("[Parser Heuristic] Generating Asset Allocation dashboard from product list categories...")
        segment_totals = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        segment_names = {
            1: "Liquid Fund",
            2: "Corporate Bond Fund",
            3: "Multi Asset Allocation Fund",
            4: "Flexi Cap Fund"
        }
        segment_objectives = {
            1: "Keeps a portion of your money safe, highly reliable, and easily accessible overnight.",
            2: "Invests in high-quality corporate debt papers to secure stable interest yields with capital preservation.",
            3: "Spreads your wealth across uncorrelated assets like equity, debt, and gold to smooth returns through cycles.",
            4: "Invests dynamically across large, mid, and small cap companies to optimize capital returns in active markets."
        }
        
        for p in products_list:
            part = p.get("Part", 4)
            amt_val = clean_float_val(str(p.get("Allocation (INR)", "0")))
            segment_totals[part] += amt_val
            
        for part in [1, 2, 3, 4]:
            pct = 0
            if total_amt > 0:
                pct = round((segment_totals[part] / total_amt) * 100)
            allocation_list.append({
                "Part": part,
                "Segment Name": segment_names[part],
                "Allocation %": pct,
                "Objective": segment_objectives[part]
            })
                
        total_pct = sum(a["Allocation %"] for a in allocation_list)
        if total_pct > 0 and total_pct != 100 and len(allocation_list) > 0:
            diff = 100 - total_pct
            largest = max(allocation_list, key=lambda x: x["Allocation %"])
            largest["Allocation %"] += diff

    # Missing critical fields check & fill defaults
    if not products_list or len(products_list) == 0:
        raise ValueError("No recommended products/funds could be detected in the uploaded Excel file. Please ensure the file contains a table with columns for Product/Fund Name and Lumpsum/SIP Amount.")

    if not client_info.get("Client Name"):
        client_info["Client Name"] = "Valued Client"
    if not client_info.get("Portfolio Corpus (INR)"):
        client_info["Portfolio Corpus (INR)"] = "10,00,00,000"
    if not firm_info.get("Firm Name"):
        firm_info["Firm Name"] = "Samarth Wealth"
        
    return {
        "firm": firm_info,
        "client": client_info,
        "allocation": allocation_list,
        "products": products_list,
        "missing_fields": [],
        "sheets": list(xl.keys()),
        "allocation_columns": allocation_cols,
        "products_columns": products_cols,
        "filepath": filepath,
        "has_swp": has_swp
    }
