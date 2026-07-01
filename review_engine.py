import os
import pandas as pd
import numpy as np

def clean_float(val):
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace("%", "").replace(" ", "").strip()
    if not val_str or val_str == "nan":
        return 0.0
    
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1].strip()
        
    try:
        f = float(val_str)
        return -f if is_negative else f
    except ValueError:
        return 0.0

def classify_asset_class(fund_name):
    name = str(fund_name).lower()
    if any(x in name for x in ["balanced advantage", "baf", "hybrid", "arbitrage", "multi asset", "multi-asset", "multiasset", "equity savings"]):
        return "Hybrid"
    if any(x in name for x in ["liquid", "debt", "bond", "gilt", "overnight", "treasury", "credit risk", "low duration", "money market", "short duration", "ultra short", "medium duration", "floater", "banking & psu", "banking and psu"]):
        return "Debt"
    if any(x in name for x in ["gold", "silver", "commodity", "alternative"]):
        return "Gold/Alternatives"
    return "Equity"

def classify_mf_category(fund_name):
    name = str(fund_name).lower()
    if "large cap" in name or "large-cap" in name or "largecap" in name or "bluechip" in name or "frontline" in name:
        return "Large Cap"
    elif "flexi cap" in name or "flexi-cap" in name or "flexicap" in name:
        return "Flexi Cap"
    elif "mid cap" in name or "mid-cap" in name or "midcap" in name or "growth opportunities" in name:
        return "Mid Cap"
    elif "small cap" in name or "small-cap" in name or "smallcap" in name:
        return "Small Cap"
    elif "balanced advantage" in name or "baf" in name or "balanced" in name or "hybrid" in name or "arbitrage" in name or "equity savings" in name:
        if "multi asset" in name or "multi-asset" in name or "multiasset" in name:
            return "Multi Asset"
        return "Hybrid"
    elif "multi asset" in name or "multi-asset" in name or "multiasset" in name:
        return "Multi Asset"
    elif "elss" in name or "tax saver" in name or "tax plan" in name or "tax shield" in name:
        return "ELSS"
    elif "liquid" in name or "debt" in name or "bond" in name or "gilt" in name or "overnight" in name or "treasury" in name or "low duration" in name or "money market" in name or "savings fund" in name or "short term" in name:
        return "Debt"
    elif "sector" in name or "thematic" in name or "pharma" in name or "banking" in name or "technology" in name or "digital" in name or "infrastructure" in name or "healthcare" in name or "fmcg" in name or "auto" in name or "special opportunities" in name or "india opportunities" in name or "business cycle" in name:
        return "Sector/Thematic"
    return "Flexi Cap"

def parse_review_excel(filepath):
    """
    Parses the Portfolio Review Excel template or raw single-sheet valuation reports.
    Returns a structured dictionary matching the Target Context Format.
    """
    print(f"[Review Engine] Parsing Excel file: {filepath}")
    try:
        xl = pd.read_excel(filepath, sheet_name=None, header=None)
    except Exception as e:
        print(f"[Review Engine ERROR] Failed reading Excel: {str(e)}")
        raise ValueError(f"Corrupted or invalid Excel spreadsheet: {str(e)}")
        
    client_info = {}
    holdings_list = []
    target_allocation = {}
    
    # 1. Sheet identification
    client_sheet_name = None
    for name in xl.keys():
        if "client" in name.lower():
            client_sheet_name = name
            break
            
    holdings_sheet_name = None
    for name in xl.keys():
        if "holding" in name.lower() or "product" in name.lower() or "report" in name.lower() or "valuation" in name.lower():
            holdings_sheet_name = name
            break
            
    is_single_sheet = len(xl) == 1
    if is_single_sheet:
        client_sheet_name = list(xl.keys())[0]
        holdings_sheet_name = list(xl.keys())[0]
    else:
        if not client_sheet_name:
            client_sheet_name = list(xl.keys())[0]
        if not holdings_sheet_name:
            holdings_sheet_name = list(xl.keys())[1] if len(xl) > 1 else list(xl.keys())[0]
            
    df_client = xl[client_sheet_name].fillna("")
    
    # Find holdings header row first to know boundaries
    header_row_idx = 0
    df_holdings_raw = xl[holdings_sheet_name].fillna("")
    for idx, row in df_holdings_raw.iterrows():
        row_vals = [str(x).lower().strip() for x in row]
        if any(any(alias.lower() in val for alias in ["product name", "fund name", "scheme name", "particulars", "scheme"]) for val in row_vals):
            header_row_idx = idx
            break
            
    # 2. Extract Client Name & Info
    client_name = "Valued Client"
    if is_single_sheet:
        found_client = False
        for r in range(header_row_idx):
            for c in range(df_client.shape[1]):
                val = str(df_client.iloc[r, c]).strip()
                if any(val.lower().startswith(pfx) for pfx in ["mr. ", "mrs. ", "ms. ", "dr. ", "shri ", "smt "]):
                    client_name = val
                    found_client = True
                    break
            if found_client:
                break
        if not found_client:
            # Fallback scan backwards
            for r in range(header_row_idx - 1, -1, -1):
                for c in [1, 0]:
                    if c < df_client.shape[1]:
                        val = str(df_client.iloc[r, c]).strip()
                        if val and val.lower() not in ["nan", "", "portfolio valuation report", "samarth wealth", "samarth wealth pvt. ltd.", "valuation report"]:
                            client_name = val
                            found_client = True
                            break
                if found_client:
                    break
                    
        client_data = {
            "client_name": client_name,
            "report_date": "June 2026",
            "horizon": "5+ Years",
            "risk_profile": "Moderate-Aggressive",
            "primary_objective": "Wealth Compounding",
            "tax_bracket": "30%",
            "portfolio_value_inr": 0.0,
            "total_purchase_cost_inr": 0.0
        }
    else:
        # Parse Client_Info sheet as key-value pairs
        client_info = {}
        for idx, row in df_client.iterrows():
            if len(row) >= 2:
                k = str(row.iloc[0]).strip()
                v = str(row.iloc[1]).strip()
                if k and k != "FIELD":
                    client_info[k] = v
        client_data = {
            "client_name": client_info.get("Client Name", "Valued Client"),
            "report_date": client_info.get("Report Date", "June 2026"),
            "horizon": client_info.get("Investment Horizon", "5+ Years"),
            "risk_profile": client_info.get("Risk Profile", "Moderate-Aggressive"),
            "primary_objective": client_info.get("Primary Objective", "Wealth Compounding"),
            "tax_bracket": client_info.get("Tax Bracket", "30%"),
            "portfolio_value_inr": 0.0,
            "total_purchase_cost_inr": 0.0
        }
        
    # 3. Parse Current_Holdings
    df_holdings = xl[holdings_sheet_name]
    df_holdings.columns = [str(x).strip() for x in df_holdings.iloc[header_row_idx]]
    df_holdings_data = df_holdings.iloc[header_row_idx+1:].fillna("")
    
    col_mapping = {
        "product_name": ["Product Name", "Product", "Fund Name", "Fund", "Scheme", "Scheme Name", "Investment"],
        "asset_class": ["Asset Class", "Class", "Instrument Type", "Instrument"],
        "category": ["Category", "Segment", "AMFI Category"],
        "current_value_inr": ["Current Value (INR)", "Current Value", "Value", "Market Value", "Value (INR)", "Amount", "Present Market Value"],
        "purchase_cost_inr": ["Purchase Cost (INR)", "Purchase Cost", "Invested Amount", "Cost", "Invested Value", "Purchase Value"],
        "expense_ratio_pct": ["Expense Ratio (%)", "Expense Ratio", "Expense Ratio (%)", "Expense Ratio %", "Expense %"],
        "sharpe_ratio": ["Sharpe Ratio", "Sharpe", "Risk Sharpe"],
        "one_year_return_pct": ["1Y Return (%)", "1Y Return", "1 Year Return", "1Y Return %", "1 Year Return %"],
        "three_year_return_pct": ["3Y Return (%)", "3Y Return", "3 Year Return", "3Y Return %", "3 Year Return %"],
        "benchmark_one_year_return_pct": ["Benchmark Return (%)", "Benchmark 1Y Return", "Benchmark Return", "Index Return"],
        "purchase_date": ["Purchase Date", "Date of Purchase", "Investment Date", "Inv. Since"],
        "sip_amount": ["SIP Amount", "Monthly SIP", "SIP", "SIP Value", "SIP Amount (INR)"],
        "xirr_pct": ["XIRR%", "XIRR (%)", "XIRR", "Annualized Return", "XIRR %"],
        "advisor_notes": ["Review & Recommendations", "Review", "Recommendations", "Advisor Remarks", "Remarks", "Comments", "Advisor Recommendations"]
    }
    
    actual_cols = {}
    for canonical, aliases in col_mapping.items():
        matched = False
        for col in df_holdings.columns:
            if any(alias.lower() == col.lower() for alias in aliases):
                actual_cols[canonical] = col
                matched = True
                break
        if not matched:
            for col in df_holdings.columns:
                if any(alias.lower() in col.lower() for alias in aliases):
                    actual_cols[canonical] = col
                    break
                    
    total_value = 0.0
    total_cost = 0.0
    
    for idx, row in df_holdings_data.iterrows():
        p_name = str(row.get(actual_cols.get("product_name"), "")).strip()
        if not p_name or p_name.lower() in ["total", "grand total", "none", "", "nan"]:
            continue
            
        cur_val = clean_float(row.get(actual_cols.get("current_value_inr"), 0.0))
        pur_cost = clean_float(row.get(actual_cols.get("purchase_cost_inr"), 0.0))
        
        # Calculate individual fund return gain/loss
        gain_loss_inr = cur_val - pur_cost
        gain_loss_pct = (gain_loss_inr / pur_cost * 100.0) if pur_cost > 0.0 else 0.0
        
        # Dynamic Asset Class detection
        asset_class_col = actual_cols.get("asset_class")
        if asset_class_col and asset_class_col in row:
            asset_class = str(row.get(asset_class_col)).strip()
        else:
            asset_class = classify_asset_class(p_name)
            
        # Classify categories using the specific 9 mutual fund categories requested
        category = classify_mf_category(p_name)
            
        # Fallbacks for ratios if not in sheet
        exp_col = actual_cols.get("expense_ratio_pct")
        if exp_col and exp_col in row and row.get(exp_col) != "":
            exp_ratio = clean_float(row.get(exp_col))
        else:
            if asset_class == "Equity":
                exp_ratio = 0.65
            elif asset_class == "Debt":
                exp_ratio = 0.25
            elif asset_class == "Hybrid":
                exp_ratio = 0.55
            else:
                exp_ratio = 0.40
                
        sharpe_col = actual_cols.get("sharpe_ratio")
        if sharpe_col and sharpe_col in row and row.get(sharpe_col) != "":
            sharpe = clean_float(row.get(sharpe_col))
        else:
            if asset_class == "Equity":
                sharpe = 1.25
            elif asset_class == "Debt":
                sharpe = 1.65
            elif asset_class == "Hybrid":
                sharpe = 1.15
            else:
                sharpe = 0.80
                
        ret_1y = clean_float(row.get(actual_cols.get("one_year_return_pct"), 0.0))
        ret_3y = clean_float(row.get(actual_cols.get("three_year_return_pct"), 0.0))
        bench_ret = clean_float(row.get(actual_cols.get("benchmark_one_year_return_pct"), 0.0))
        pur_date = str(row.get(actual_cols.get("purchase_date"), "")).strip()
        
        # Extract SIP, XIRR, and Advisor remarks
        sip_col = actual_cols.get("sip_amount")
        sip_amt = clean_float(row.get(sip_col)) if sip_col and sip_col in row else 0.0
        
        xirr_col = actual_cols.get("xirr_pct")
        xirr_val = clean_float(row.get(xirr_col)) if xirr_col and xirr_col in row else 0.0
        
        notes_col = actual_cols.get("advisor_notes")
        adv_notes = str(row.get(notes_col)).strip() if notes_col and notes_col in row else ""
        if adv_notes.lower() == "nan":
            adv_notes = ""
        
        holding = {
            "product_name": p_name,
            "asset_class": asset_class,
            "category": category,
            "current_value_inr": cur_val,
            "purchase_cost_inr": pur_cost,
            "allocation_pct": 0.0,
            "gain_loss_pct": round(gain_loss_pct, 2),
            "gain_loss_inr": round(gain_loss_inr, 2),
            "expense_ratio_pct": exp_ratio,
            "sharpe_ratio": sharpe,
            "one_year_return_pct": ret_1y if ret_1y > 0.0 else round(gain_loss_pct, 2),
            "three_year_return_pct": ret_3y,
            "benchmark_one_year_return_pct": bench_ret,
            "purchase_date": pur_date,
            "sip_amount": sip_amt,
            "xirr_pct": xirr_val,
            "advisor_notes": adv_notes
        }
        holdings_list.append(holding)
        total_value += cur_val
        total_cost += pur_cost
        
    client_data["portfolio_value_inr"] = total_value
    client_data["total_purchase_cost_inr"] = total_cost
    client_data["total_sip_amount"] = sum(h["sip_amount"] for h in holdings_list)
    client_data["portfolio_xirr_pct"] = round(sum(h["xirr_pct"] * (h["current_value_inr"] / total_value) for h in holdings_list), 2) if total_value > 0.0 else 0.0
    
    # Calculate weights
    for h in holdings_list:
        h["allocation_pct"] = round((h["current_value_inr"] / total_value * 100.0), 2) if total_value > 0.0 else 0.0
        
    # 4. Target Allocation sheet (if multi-sheet)
    if not is_single_sheet:
        target_sheet_name = None
        for name in xl.keys():
            if "target" in name.lower() or "allocation" in name.lower():
                target_sheet_name = name
                break
        if target_sheet_name:
            df_target = xl[target_sheet_name].fillna("")
            for idx, row in df_target.iterrows():
                if len(row) >= 2:
                    ac = str(row.iloc[0]).strip()
                    pct_val = row.iloc[1]
                    if ac and ac.lower() not in ["asset class", "field", "value", "target allocation (%)", "target"]:
                        target_allocation[ac] = clean_float(pct_val)
                        
    # Fallback to standard targets if empty
    if not target_allocation:
        target_allocation = {
            "Equity": 60.0,
            "Debt": 30.0,
            "Hybrid": 5.0,
            "Gold/Alternatives": 5.0
        }
        
    # Calculate current asset class allocation breakdown
    current_allocation = {}
    for h in holdings_list:
        ac = h["asset_class"]
        current_allocation[ac] = current_allocation.get(ac, 0.0) + h["current_value_inr"]
        
    current_allocation_pct = {}
    for ac, val in current_allocation.items():
        current_allocation_pct[ac] = round((val / total_value * 100.0), 2) if total_value > 0.0 else 0.0
        
    # Ensure all target keys exist in current
    for ac in target_allocation.keys():
        if ac not in current_allocation_pct:
            current_allocation_pct[ac] = 0.0
            
    # Calculate variance
    allocation_variance = {}
    for ac, target_pct in target_allocation.items():
        curr_pct = current_allocation_pct.get(ac, 0.0)
        var_pct = curr_pct - target_pct
        
        rebalance_action = "Maintain"
        if var_pct > 2.5:
            rebalance_action = "Trim / Reduce"
        elif var_pct < -2.5:
            rebalance_action = "Accumulate / Buy"
            
        allocation_variance[ac] = {
            "current_pct": curr_pct,
            "target_pct": target_pct,
            "variance_pct": round(var_pct, 2),
            "rebalance_action": rebalance_action
        }
        
    # Calculate category allocation breakdown
    target_category_allocation = {
        "Large Cap": 30.0,
        "Flexi Cap": 20.0,
        "Mid Cap": 15.0,
        "Small Cap": 10.0,
        "Hybrid": 10.0,
        "Multi Asset": 5.0,
        "Sector/Thematic": 5.0,
        "ELSS": 5.0,
        "Debt": 0.0
    }
    
    category_allocation = {}
    for h in holdings_list:
        cat = h["category"]
        category_allocation[cat] = category_allocation.get(cat, 0.0) + h["current_value_inr"]
        
    category_allocation_pct = {}
    for cat, val in category_allocation.items():
        category_allocation_pct[cat] = round((val / total_value * 100.0), 2) if total_value > 0.0 else 0.0
        
    for cat in target_category_allocation.keys():
        if cat not in category_allocation_pct:
            category_allocation_pct[cat] = 0.0
            
    category_variance = {}
    for cat, target_pct in target_category_allocation.items():
        curr_pct = category_allocation_pct.get(cat, 0.0)
        var_pct = curr_pct - target_pct
        
        rebalance_action = "Maintain"
        if var_pct > 2.5:
            rebalance_action = "Trim / Reduce"
        elif var_pct < -2.5:
            rebalance_action = "Accumulate / Buy"
            
        category_variance[cat] = {
            "current_pct": curr_pct,
            "target_pct": target_pct,
            "variance_pct": round(var_pct, 2),
            "rebalance_action": rebalance_action
        }
        
    # Weighted averages
    weighted_expense = 0.0
    weighted_sharpe = 0.0
    for h in holdings_list:
        w = h["allocation_pct"] / 100.0
        weighted_expense += w * h["expense_ratio_pct"]
        weighted_sharpe += w * h["sharpe_ratio"]
        
    # Health Score Calculation
    xirr_val = client_data["portfolio_xirr_pct"]
    if xirr_val >= 15.0:
        returns_score = 20
    elif xirr_val >= 10.0:
        returns_score = 16
    elif xirr_val >= 7.0:
        returns_score = 12
    else:
        returns_score = 8

    # Diversification Score (out of 20)
    num_holdings = len(holdings_list)
    max_weight = max(h["allocation_pct"] for h in holdings_list) if holdings_list else 100.0
    div_score = 20
    if num_holdings < 4:
        div_score -= 5
    elif num_holdings > 15:
        div_score -= 3
    if max_weight > 30.0:
        div_score -= 4
    div_score = max(5, div_score)

    # Risk Management Score (out of 20)
    if weighted_sharpe >= 1.3:
        risk_score = 20
    elif weighted_sharpe >= 1.0:
        risk_score = 16
    elif weighted_sharpe >= 0.7:
        risk_score = 12
    else:
        risk_score = 8

    # Asset Allocation Score (out of 20)
    total_variance = sum(abs(v["variance_pct"]) for v in allocation_variance.values())
    if total_variance <= 10.0:
        aa_score = 20
    elif total_variance <= 25.0:
        aa_score = 16
    elif total_variance <= 40.0:
        aa_score = 12
    else:
        aa_score = 8

    # Long-Term Potential Score (out of 20)
    underperforming_count = sum(1 for h in holdings_list if h["xirr_pct"] < 8.0)
    lt_score = max(10, 20 - underperforming_count * 2)

    health_total = returns_score + div_score + risk_score + aa_score + lt_score
    if health_total >= 85:
        health_rating = "STRONG (EXCELLENT)"
    elif health_total >= 70:
        health_rating = "BALANCED (HEALTHY)"
    elif health_total >= 50:
        health_rating = "CAUTION (NEEDS REBALANCING)"
    else:
        health_rating = "WEAK (CRITICAL AUDIT REQUIRED)"

    health_data = {
        "returns": returns_score,
        "diversification": div_score,
        "risk_management": risk_score,
        "asset_allocation": aa_score,
        "long_term_potential": lt_score,
        "total": health_total,
        "rating": health_rating
    }

    # Top Performing Funds (ranked by XIRR descending)
    top_performers = sorted(holdings_list, key=lambda x: x["xirr_pct"], reverse=True)[:5]
    
    # Funds Requiring Attention
    attention_funds = []
    for h in holdings_list:
        notes = h["advisor_notes"].lower()
        is_underperformer = h["xirr_pct"] < 8.0 or h["gain_loss_pct"] < 0.0
        is_marked = any(w in notes for w in ["redeem", "switch", "sell", "review", "attention", "underperform", "under-perform", "lagging"])
        
        if is_underperformer or is_marked:
            reasons = []
            if h["xirr_pct"] < 8.0:
                reasons.append("Low annualized return (XIRR < 8.0%)")
            if h["gain_loss_pct"] < 0.0:
                reasons.append("Negative absolute gain/loss")
            if is_marked:
                reasons.append("Flagged by advisor for restructuring")
            
            reason_str = "; ".join(reasons) if reasons else "Underperforming relative to target growth"
            
            action = "Hold"
            if "redeem" in notes or "sell" in notes:
                action = "Redeem"
            elif "switch" in notes:
                action = "Switch"
            elif "increase" in notes or "accumulate" in notes:
                action = "Increase Allocation"
            elif is_underperformer:
                action = "Switch"
                
            attention_funds.append({
                "product_name": h["product_name"],
                "category": h["category"],
                "current_value_inr": h["current_value_inr"],
                "xirr_pct": h["xirr_pct"],
                "reason": reason_str,
                "action": action
            })
            
    if not attention_funds:
        lowest = min(holdings_list, key=lambda x: x["xirr_pct"]) if holdings_list else None
        if lowest:
            attention_funds.append({
                "product_name": lowest["product_name"],
                "category": lowest["category"],
                "current_value_inr": lowest["current_value_inr"],
                "xirr_pct": lowest["xirr_pct"],
                "reason": "Relatively lower return compared to peer average",
                "action": "Switch"
            })

    # Build context object
    review_context = {
        "client": client_data,
        "target_allocation": target_allocation,
        "target_category_allocation": target_category_allocation,
        "holdings": holdings_list,
        "analytics": {
            "unrealized_gain_loss_inr": round(total_value - total_cost, 2),
            "unrealized_gain_loss_pct": round(((total_value - total_cost) / total_cost * 100.0), 2) if total_cost > 0.0 else 0.0,
            "weighted_average_expense_ratio": round(weighted_expense / 100.0, 5),
            "weighted_average_sharpe_ratio": round(weighted_sharpe, 2),
            "allocation_variance": allocation_variance,
            "category_allocation": category_allocation_pct,
            "category_variance": category_variance,
            "health_score": health_data,
            "top_performers": top_performers,
            "attention_funds": attention_funds
        }
    }
    
    return review_context

def generate_review_narratives(review_context, api_key=None):
    """
    Generates professional qualitative narratives for the Portfolio Review using Gemini.
    Falls back to a dynamic rules-based text generator if the API key is missing or the call fails.
    """
    from ai_engine import call_llm_api
    import os
    import json
    
    client = review_context["client"]
    analytics = review_context["analytics"]
    variance = analytics["allocation_variance"]
    holdings = review_context["holdings"]
    
    # 1. Generate local rule-based fallback narratives first
    overweighted = []
    underweighted = []
    for ac, data in variance.items():
        if data["variance_pct"] > 2.5:
            overweighted.append(f"{ac} (+{data['variance_pct']}%)")
        elif data["variance_pct"] < -2.5:
            underweighted.append(f"{ac} ({data['variance_pct']}%)")
            
    drift_desc = ""
    if overweighted and underweighted:
        drift_desc = f"The portfolio currently exhibits asset-class drift, with an overweight position in {', '.join(overweighted)} and an underweight position in {', '.join(underweighted)}."
    elif overweighted:
        drift_desc = f"The portfolio exhibits overweight positions in {', '.join(overweighted)}, exceeding target allocation bounds."
    elif underweighted:
        drift_desc = f"The portfolio shows underweight gaps in {', '.join(underweighted)}, which could limit return compounding."
    else:
        drift_desc = "The portfolio is currently well-balanced and closely aligned with the target asset allocation matrix."
        
    fallback_exec_summary = (
        f"We have executed a diagnostic wealth audit for the portfolio of {client['client_name']}. "
        f"The aggregate holdings, valued at INR {int(client['portfolio_value_inr']):,}, have generated absolute "
        f"wealth of INR {int(analytics['unrealized_gain_loss_inr']):,} representing an absolute gain of "
        f"{analytics['unrealized_gain_loss_pct']}%. The portfolio exhibits a robust annualized compounding XIRR of "
        f"{client['portfolio_xirr_pct']}%, confirming strong active manager selection. However, the asset allocation "
        f"matrix reveals a structural drift with an overweight equity bias and a fixed-income deficit. "
        f"Rebalancing is recommended to protect accrued gains and moderate portfolio standard deviation."
    )
    
    fallback_macro_outlook = {
        "equity": "Equities remain supported by robust corporate earnings and strong domestic consumption, though select sectors trade at premium valuations.",
        "interest_rate": "The interest rate cycle is peaking, suggesting that locking in yields via high-quality debt assets is a prudent defensive strategy.",
        "economic": "India's macroeconomic fundamentals are resilient, supported by healthy GDP growth, manageable inflation, and consistent capital inflows.",
        "investment_strategy": "Maintain a balanced asset allocation, systematically booking profits in high-valuation segments and compounding through SIPs."
    }
    
    fallback_strengths = [
        "🏆 Core Equity Quality: Primary holdings in flexi-cap and mid-cap segments exhibit strong information ratios and positive manager alpha, consistently outperforming benchmark indices.",
        "📈 Wealth Compounding Velocity: Invested capital demonstrates high compounding efficiency, generating a robust absolute return profile driven by sector-tailored stock selection.",
        "💼 Institutional Manager Selection: Core funds are managed by high-conviction teams displaying disciplined investment frameworks and optimal downside capture ratios."
    ]
    
    fallback_improvements = [
        "⚠️ Structural Asset Drift: Equity overweight relative to target bounds exposes the portfolio to heightened cyclical drawdowns; systematic fixed-income hedging is required.",
        "📉 Tail-End Consolidation Opportunity: Multiple tail-end holdings with allocations under 2.5% create administrative drag without contributing meaningful performance compounding.",
        "❌ Yield Leakage in Debt Sleeves: Sub-optimal yield-to-maturity (YTM) in conservative allocations; capital should be reallocated to lock in high-quality yields at the peak of the interest rate cycle."
    ]
    
    fallback_recommendations = {
        "continue_holdings": "Continue holding core compounding anchors like Parag Parikh Flexi Cap to sustain long-term manager alpha and capture global equity diversification.",
        "switch": "Execute a phased switch from tail-end underperforming thematic schemes into high-conviction diversified flexi-caps to eliminate performance drag.",
        "rebalancing": "Book profits systematically in overweighted equity segments to restore the target 70% equity allocation, reallocating proceeds to fixed-income buffers.",
        "additional_investments": "Deploy incremental surpluses into high-quality corporate bonds and multi-asset funds to capture peaking yields and introduce commodity hedges.",
        "risk_management": "Integrate dynamic hybrid and balanced advantage (BAF) sleeves to moderate portfolio beta and provide downside protection during corrections."
    }
    
    fallback_audits = {}
    for h in holdings:
        name = h["product_name"]
        cat = h["category"]
        ret = h["xirr_pct"]
        if ret >= 15.0:
            fallback_audits[name] = f"Reviewed due to strong compounding performance. Recommended to Continue Holding as a core compounding anchor. Expected benefit is steady capital expansion backed by high manager alpha and robust downside capture protection."
        elif ret >= 8.0:
            fallback_audits[name] = f"Reviewed due to moderate performance. Recommended to Hold and Monitor Closely. Expected benefit is maintaining broad category exposure and diversification without realizing short-term paper losses during sectoral market consolidations."
        else:
            fallback_audits[name] = f"Reviewed due to persistent underperformance relative to benchmark. Recommended to Switch out of this scheme. Expected benefit is the eradication of trailing return drag and consolidation of capital into higher-conviction peer managers."
            
    # 2. Build prompt context
    client_summary = f"Client: {client['client_name']}, Horizon: {client['horizon']}, Risk Profile: {client['risk_profile']}, Objective: {client['primary_objective']}"
    portfolio_value = f"Total Portfolio Value: INR {int(client['portfolio_value_inr']):,}, Cost: INR {int(client['total_purchase_cost_inr']):,}, Unrealized Gain: INR {int(analytics['unrealized_gain_loss_inr']):,} ({analytics['unrealized_gain_loss_pct']}%)"
    
    alloc_summary = "Current vs Target Allocations and Variances:\n"
    for ac, data in variance.items():
        alloc_summary += f"- {ac}: Current {data['current_pct']}%, Target {data['target_pct']}%, Variance {data['variance_pct']}%, Recommended Action: {data['rebalance_action']}\n"
        
    holdings_summary = "Current Portfolio Holdings:\n"
    for idx, h in enumerate(holdings, 1):
        holdings_summary += f"{idx}. {h['product_name']} | Class: {h['asset_class']} | Cat: {h['category']} | Weight: {h['allocation_pct']}% | Return: {h['one_year_return_pct']}% | Sharpe: {h['sharpe_ratio']} | Expense: {h['expense_ratio_pct']}%\n"
        
    prompt = f"""
You are a premium private wealth advisor at Samarth Wealth. 
Analyze the client's mutual fund portfolio audit and generate professional, qualitative commentary.
Simplify any complex financial jargon to make it client-friendly (e.g. explain that Sharpe ratio means risk-adjusted return efficiency, and volatility means market ups and downs).
Do not use generic placeholder text.

{client_summary}
{portfolio_value}
{alloc_summary}
{holdings_summary}

Please return a valid JSON object with the following fields:
1. "executive_summary": A 3-4 sentence comprehensive, client-friendly evaluation of their overall portfolio health, noting any major drift from targets.
2. "macro_outlook": A JSON object with keys "equity", "interest_rate", "economic", and "investment_strategy", each containing a 1-2 sentence outlook summary.
3. "portfolio_strengths": An array of 3 clear, unique bullet points highlighting the strengths of the portfolio.
4. "portfolio_improvements": An array of 3 clear, unique bullet points highlighting the areas of improvement.
5. "recommendations": A JSON object with keys "continue_holdings", "switch", "rebalancing", "additional_investments", and "risk_management", each containing a 1-2 sentence actionable description.
6. "fund_audits": A JSON dictionary mapping EACH fund's product name to a specific, unique 1-2 sentence performance audit or suitability rationale.

Ensure the output is strictly valid JSON format. Do not enclose in markdown blocks other than JSON.
"""

    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            print("[Review Engine] Engaging Gemini/OpenAI API for Portfolio Review Narratives...")
            raw_response = call_llm_api(prompt, api_key)
            
            clean_resp = raw_response.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp[7:]
            if clean_resp.endswith("```"):
                clean_resp = clean_resp[:-3]
            clean_resp = clean_resp.strip()
            
            res_dict = json.loads(clean_resp)
            
            narratives = {
                "executive_summary": res_dict.get("executive_summary", fallback_exec_summary),
                "macro_outlook": res_dict.get("macro_outlook", fallback_macro_outlook),
                "portfolio_strengths": res_dict.get("portfolio_strengths", fallback_strengths),
                "portfolio_improvements": res_dict.get("portfolio_improvements", fallback_improvements),
                "recommendations": res_dict.get("recommendations", fallback_recommendations),
                "fund_audits": res_dict.get("fund_audits", fallback_audits)
            }
            # Make sure fund audits has entries for all holdings
            for h in holdings:
                name = h["product_name"]
                if name not in narratives["fund_audits"]:
                    narratives["fund_audits"][name] = fallback_audits.get(name, "Audit pending. Maintain current position.")
                    
            print("[Review Engine] Generative Narratives generated successfully.")
            return narratives
        except Exception as e:
            print(f"[Review Engine WARN] LLM call failed or returned invalid JSON: {str(e)}. Using fallback narratives.")
            
    print("[Review Engine] Rules-based fallback narratives activated.")
    return {
        "executive_summary": fallback_exec_summary,
        "macro_outlook": fallback_macro_outlook,
        "portfolio_strengths": fallback_strengths,
        "portfolio_improvements": fallback_improvements,
        "recommendations": fallback_recommendations,
        "fund_audits": fallback_audits
    }

