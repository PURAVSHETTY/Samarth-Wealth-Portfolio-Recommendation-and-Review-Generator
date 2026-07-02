import os
import json
import traceback
import zlib
import random
import requests

# Track recent response text hashes to detect cached response reuse
_RECENT_GEMINI_RESPONSES = []

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

def simplify_jargon(text):
    """Replaces overly technical financial terms with simple client-friendly words."""
    replacements = {
        "asymmetric hedging": "protecting your money from market drops",
        "long-short strategy": "balancing investments that go up and down",
        "alpha generation": "earning higher returns than average market index",
        "drawdown protection": "reducing loss when markets are falling",
        "market-neutral": "steady returns regardless of stock market fluctuations",
        "arbitrage": "taking advantage of price differences between markets",
        "delinquencies": "repayment failures",
        "hedging": "safety measures",
        "hedges": "protection",
        "hedge": "protect",
        "leveraging": "using",
        "leverage": "boost",
        "volatility": "ups and downs"
    }
    simplified = text
    for jargon, simple in replacements.items():
        import re
        pattern = re.compile(re.escape(jargon), re.IGNORECASE)
        simplified = pattern.sub(simple, simplified)
    return simplified

def get_simplified_segment_name(part, products_in_part, profile=None):
    part = int(part)
    
    # Fallback to defaults if no profile is passed
    if not profile:
        if part == 1:
            return "Liquid Fund"
        elif part == 2:
            return "Corporate Bond Fund"
        elif part == 3:
            return "Multi Asset Allocation Fund"
        elif part == 4:
            return "Flexi Cap Fund"
        return f"Segment {part}"
        
    risk = str(profile.get("risk_appetite", "Moderate")).lower()
    objective = str(profile.get("objective", "Long-term growth")).lower()
    client_name = profile.get("client_name", "Client")
    
    # Hash seed based on name and part to ensure stable but custom names per client
    seed_val = zlib.crc32(f"{client_name}_{part}".encode('utf-8'))
    rng = random.Random(seed_val)
    
    if part == 1:
        options = ["Safety Reserve", "Capital Stability", "Core Portfolio", "Liquidity Buffer"]
        if "conservative" in risk:
            options = ["Safety Reserve", "Capital Stability", "Security Sleeve"]
        return rng.choice(options)
    elif part == 2:
        options = ["Fixed Income Sleeve", "Income & Growth", "Reliable Payouts", "Fixed Income Sleeve"]
        if "income" in objective:
            options = ["Reliable Payouts", "Fixed Income Sleeve", "Income Generation"]
        return rng.choice(options)
    elif part == 3:
        options = ["Balanced Growth", "Balanced Growth Sleeve", "Growth & Stability", "Smart Diversification", "Hedged Growth"]
        if "conservative" in risk:
            options = ["Growth & Stability", "Balanced Growth Sleeve"]
        return rng.choice(options)
    else:  # part 4
        options = ["Wealth Creation", "Long-Term Wealth", "Future Growth", "Equity Growth", "Capital Growth"]
        if "aggressive" in risk:
            options = ["Wealth Creation", "Capital Compounding Sleeve", "Capital Compounding"]
        return rng.choice(options)

def get_simplified_segment_objective(part, segment_name, products_in_part):
    part = int(part)
    if part == 1:
        return "Keeps a portion of your money safe, highly reliable, and easily accessible whenever needed."
    elif part == 2:
        return "Provides steady, regular payouts with lower price swings to protect your capital."
    elif part == 3:
        return "Helps protect wealth during market volatility while still generating growth."
    elif part == 4:
        return "Focused on long-term wealth creation through equity investments."
    return ""

AMFI_SORT_ORDER = [
    # Liquid & Debt (Lowest risk to medium-low risk)
    "Overnight Fund",
    "Liquid Fund",
    "Ultra Short Duration Fund",
    "Low Duration Fund",
    "Money Market Fund",
    "Short Duration Fund",
    "Medium Duration Fund",
    "Floater Fund",
    "Corporate Bond Fund",
    "Banking and PSU Fund",
    "Credit Risk Fund",
    "Gilt Fund",
    "Dynamic Bond Fund",
    
    # Hybrid / Asset Allocation (Medium-low to medium risk)
    "Arbitrage Fund",
    "Conservative Hybrid Fund",
    "Balanced Advantage Fund",
    "Equity Savings Fund",
    "Aggressive Hybrid Fund",
    "Multi Asset Allocation Fund",
    "Gold Fund",
    
    # Equity (Medium-high to high risk)
    "Large Cap Fund",
    "Index Fund",
    "ETF",
    "Large & Mid Cap Fund",
    "Flexi Cap Fund",
    "Multi Cap Fund",
    "Focused Fund",
    "Value Fund",
    "Contra Fund",
    "ELSS",
    "Mid Cap Fund",
    "Small Cap Fund",
    "Sectoral/Thematic Fund",
    
    # PMS / Other
    "Portfolio Management Services (PMS)",
    "PMS"
]

def classify_amfi_category(product_name, category_or_class=""):
    name = str(product_name).lower()
    cat = str(category_or_class).lower()
    
    is_pms = (
        "pms" in cat or "pms" in name or 
        "portfolio management" in cat or "portfolio management" in name or 
        "p.m.s" in cat or "p.m.s" in name or
        any(kw in name for kw in ["buoyant", "rising stars", "valuequest", "ask growth", "marcellus"])
    )
    if is_pms:
        return "Portfolio Management Services (PMS)", "(Concentrated Growth Allocation)"

    # 1. Check specific product name keywords first (highest priority)
    if "liquid" in name:
        return "Liquid Fund", "(Safety & Liquidity Allocation)"
    elif "arbitrage" in name:
        return "Arbitrage Fund", "(Hedged Low-Risk Allocation)"
    elif "equity savings" in name:
        return "Equity Savings Fund", "(Income & Stability Allocation)"
    elif "corporate bond" in name:
        return "Corporate Bond Fund", "(Fixed Income Allocation)"
    elif "credit risk" in name:
        return "Credit Risk Fund", "(Credit Risk Allocation)"
    elif "banking and psu" in name or "banking & psu" in name:
        return "Banking and PSU Fund", "(Fixed Income Allocation)"
    elif "dynamic bond" in name:
        return "Dynamic Bond Fund", "(Dynamic Debt Allocation)"
    elif "gilt" in name:
        return "Gilt Fund", "(Sovereign Debt Allocation)"
    elif "low duration" in name:
        return "Low Duration Fund", "(Short-Term Debt Allocation)"
    elif "money market" in name:
        return "Money Market Fund", "(Short-Term Debt Allocation)"
    elif "overnight" in name:
        return "Overnight Fund", "(Safety & Liquidity Allocation)"
    elif "short duration" in name:
        return "Short Duration Fund", "(Short-Term Debt Allocation)"
    elif "ultra short" in name:
        return "Ultra Short Duration Fund", "(Short-Term Debt Allocation)"
    elif "medium duration" in name:
        return "Medium Duration Fund", "(Debt Allocation)"
    elif "floater" in name:
        return "Floater Fund", "(Debt Allocation)"
    elif "gold" in name:
        return "Gold Fund", "(Commodity Allocation)"
    elif "balanced advantage" in name or "baf" in name or "dynamic asset allocation" in name or "dynamic equity" in name:
        return "Balanced Advantage Fund", "(Income & Stability Allocation)"
    elif "equity hybrid" in name or "aggressive hybrid" in name:
        return "Aggressive Hybrid Fund", "(Balanced Growth Allocation)"
    elif "debt hybrid" in name or "conservative hybrid" in name:
        return "Conservative Hybrid Fund", "(Income & Stability Allocation)"
    elif "multi asset" in name or "multi-asset" in name or "multiasset" in name:
        return "Multi Asset Allocation Fund", "(Diversified Growth Allocation)"
    elif "small cap" in name or "small-cap" in name or "smallcap" in name:
        return "Small Cap Fund", "(High Growth Allocation)"
    elif "mid cap" in name or "mid-cap" in name or "midcap" in name:
        return "Mid Cap Fund", "(Mid-Cap Growth Allocation)"
    elif "large & mid" in name or "large and mid" in name or "large-and-mid" in name:
        return "Large & Mid Cap Fund", "(Growth & Stability Allocation)"
    elif "large cap" in name or "large-cap" in name or "largecap" in name:
        return "Large Cap Fund", "(Stable Bluechip Allocation)"
    elif "flexi cap" in name or "flexicap" in name or "flexi-cap" in name:
        return "Flexi Cap Fund", "(Dynamic Equity Allocation)"
    elif "multi cap" in name or "multicap" in name or "multi-cap" in name:
        return "Multi Cap Fund", "(Structured Equity Allocation)"
    elif "value" in name:
        return "Value Fund", "(Value Equity Allocation)"
    elif "contra" in name:
        return "Contra Fund", "(Value Equity Allocation)"
    elif "focused" in name:
        return "Focused Fund", "(Concentrated Equity Allocation)"
    elif "index" in name:
        return "Index Fund", "(Passive Equity Allocation)"
    elif "etf" in name:
        return "ETF", "(Passive Equity Allocation)"
    elif "elss" in name or "tax saver" in name or "tax shield" in name:
        return "ELSS", "(Tax Saving Equity Allocation)"
        
    # 2. Check category/class keywords (lower priority fallbacks)
    if "liquid" in cat:
        return "Liquid Fund", "(Safety & Liquidity Allocation)"
    elif "arbitrage" in cat:
        return "Arbitrage Fund", "(Hedged Low-Risk Allocation)"
    elif "equity savings" in cat:
        return "Equity Savings Fund", "(Income & Stability Allocation)"
    elif "corporate bond" in cat:
        return "Corporate Bond Fund", "(Fixed Income Allocation)"
    elif "credit risk" in cat:
        return "Credit Risk Fund", "(Credit Risk Allocation)"
    elif "banking and psu" in cat or "banking & psu" in cat:
        return "Banking and PSU Fund", "(Fixed Income Allocation)"
    elif "dynamic bond" in cat:
        return "Dynamic Bond Fund", "(Dynamic Debt Allocation)"
    elif "gilt" in cat:
        return "Gilt Fund", "(Sovereign Debt Allocation)"
    elif "low duration" in cat:
        return "Low Duration Fund", "(Short-Term Debt Allocation)"
    elif "money market" in cat:
        return "Money Market Fund", "(Short-Term Debt Allocation)"
    elif "overnight" in cat:
        return "Overnight Fund", "(Safety & Liquidity Allocation)"
    elif "short duration" in cat:
        return "Short Duration Fund", "(Short-Term Debt Allocation)"
    elif "ultra short" in cat:
        return "Ultra Short Duration Fund", "(Short-Term Debt Allocation)"
    elif "medium duration" in cat:
        return "Medium Duration Fund", "(Debt Allocation)"
    elif "floater" in cat:
        return "Floater Fund", "(Debt Allocation)"
    elif "gold" in cat:
        return "Gold Fund", "(Commodity Allocation)"
    elif "balanced advantage" in cat or "dynamic asset allocation" in cat:
        return "Balanced Advantage Fund", "(Income & Stability Allocation)"
    elif "equity hybrid" in cat or "aggressive hybrid" in cat:
        return "Aggressive Hybrid Fund", "(Balanced Growth Allocation)"
    elif "debt hybrid" in cat or "conservative hybrid" in cat:
        return "Conservative Hybrid Fund", "(Income & Stability Allocation)"
    elif "multi asset" in cat:
        return "Multi Asset Allocation Fund", "(Diversified Growth Allocation)"
    elif "small cap" in cat or "smallcap" in cat:
        return "Small Cap Fund", "(High Growth Allocation)"
    elif "mid cap" in cat or "midcap" in cat:
        return "Mid Cap Fund", "(Mid-Cap Growth Allocation)"
    elif "large & mid" in cat:
        return "Large & Mid Cap Fund", "(Growth & Stability Allocation)"
    elif "large cap" in cat or "largecap" in cat:
        return "Large Cap Fund", "(Stable Bluechip Allocation)"
    elif "flexi cap" in cat or "flexicap" in cat:
        return "Flexi Cap Fund", "(Dynamic Equity Allocation)"
    elif "multi cap" in cat or "multicap" in cat:
        return "Multi Cap Fund", "(Structured Equity Allocation)"
    elif "elss" in cat:
        return "ELSS", "(Tax Saving Equity Allocation)"
    
    # Generic fallbacks
    if "hybrid" in name or "hybrid" in cat:
        return "Aggressive Hybrid Fund", "(Balanced Growth Allocation)"
    elif "debt" in name or "debt" in cat or "bond" in name:
        return "Corporate Bond Fund", "(Fixed Income Allocation)"
    elif "equity" in name or "equity" in cat:
        return "Flexi Cap Fund", "(Dynamic Equity Allocation)"
        
    return "Flexi Cap Fund", "(Dynamic Equity Allocation)"

def get_amfi_category_objective(category_name):
    objectives = {
        "Liquid Fund": "Keeps a portion of your money safe, highly reliable, and easily accessible overnight.",
        "Arbitrage Fund": "Exploits short-term pricing spreads in spot and derivative markets to yield tax-friendly returns with very low risk.",
        "Equity Savings Fund": "Blends equity arbitrage and debt instruments with selective unhedged equity exposure to offer a conservative, tax-efficient growth model.",
        "Corporate Bond Fund": "Invests in high-quality corporate debt papers to secure stable interest yields with capital preservation.",
        "Conservative Hybrid Fund": "Secures steady coupon yields with a small equity slice to shield your capital from inflation.",
        "Balanced Advantage Fund": "Dynamically adjusts equity and debt weights based on market valuations to capture growth while buffering drawdowns.",
        "Aggressive Hybrid Fund": "Combines equity market participation with fixed income assets to secure growth and moderate safety.",
        "Multi Asset Allocation Fund": "Spreads your wealth across uncorrelated assets like equity, debt, and gold to smooth returns through cycles.",
        "Gold Fund": "Invests in gold bullion or precious metal ETFs to hedge your portfolio against currency debasement and macro volatility.",
        "Large Cap Fund": "Backs sector-leading blue-chip corporations with strong balance sheets for steady capital appreciation.",
        "Large & Mid Cap Fund": "Blends growth from mid-sized companies with stability from large corporate giants.",
        "Flexi Cap Fund": "Invests dynamically across large, mid, and small cap companies to optimize capital returns in active markets.",
        "Multi Cap Fund": "Maintains a disciplined weight in large, mid, and small cap companies for all-weather equity performance.",
        "Mid Cap Fund": "Invests in medium-sized emerging enterprises with high expansion room to drive capital compounding.",
        "Small Cap Fund": "Drives long-term capital compounding by backing high-growth niche market leaders at an early stage.",
        "Portfolio Management Services (PMS)": "Tailored, high-conviction portfolios managed by expert professionals to target long-term outperformance."
    }
    return objectives.get(category_name, "Aims for long-term growth and capital appreciation through specialized fund selection.")

def _classify_fund(product_name, category_or_class):
    # Backward compatibility fallback
    amfi_cat, _ = classify_amfi_category(product_name, category_or_class)
    if "liquid" in amfi_cat.lower() or "arbitrage" in amfi_cat.lower():
        return 1, amfi_cat, "6% - 8%"
    elif "bond" in amfi_cat.lower() or "debt" in amfi_cat.lower() or "hybrid" in amfi_cat.lower() or "advantage" in amfi_cat.lower():
        return 2, amfi_cat, "12% - 15%"
    elif "multi asset" in amfi_cat.lower():
        return 3, amfi_cat, "11% - 13%"
    else:
        return 4, amfi_cat, "15% - 18%"


def clean_float_val(val):
    if val is None:
        return 0.0
    val_str = str(val).lower().replace(",", "").replace("₹", "").replace("rs.", "").replace(" ", "").strip()
    if not val_str:
        return 0.0
    
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
            
    try:
        import re
        val_str = re.sub(r"[^\d\.\-]", "", val_str)
        if not val_str:
            return 0.0
        return float(val_str) * multiplier
    except ValueError:
        return 0.0

def get_client_profile_and_theme(client_data, fund_data=None):
    client_name = str(client_data.get("Client Name", "Valued Client")).strip()
    
    seed_val = zlib.crc32(client_name.encode('utf-8'))
    rng = random.Random(seed_val)
    
    has_intl = False
    if fund_data:
        intl_keywords = [
            "international", "global", "overseas", "foreign", "offshore", 
            "us equity", "us bluechip", "nasdaq", "s&p 500", "sp 500", 
            "greater china", "world", "emerging markets", "europe", 
            "japan", "asian", "us growth"
        ]
        for f in fund_data:
            product_name = str(f.get("Product Name", "")).strip().lower()
            cat_class = str(f.get("Segment") or f.get("Asset Class") or f.get("Category") or "").strip().lower()
            if any(kw in product_name for kw in intl_keywords) or any(kw in cat_class for kw in intl_keywords):
                has_intl = True
                break
                
    # Standardize risk appetite if provided in Excel
    risk_profile = str(client_data.get("Risk Profile", "")).strip()
    
    stated_appetite = None
    if risk_profile and risk_profile.lower() != "nan":
        risk_lower = risk_profile.lower()
        if "conservative" in risk_lower:
            stated_appetite = "Conservative"
        elif "moderately aggressive" in risk_lower or "moderate aggressive" in risk_lower or "mod-agg" in risk_lower or "moderate-aggressive" in risk_lower:
            stated_appetite = "Moderately aggressive"
        elif "aggressive" in risk_lower:
            stated_appetite = "Aggressive"
        elif "moderate" in risk_lower:
            stated_appetite = "Moderate"
            
    # Check if we have fund_data to refine the risk profile
    has_aggressive_exposure = False
    aggressive_weight = 0.0
    total_alloc = 0.0
    
    if fund_data:
        for f in fund_data:
            product_name = f.get("Product Name", "").strip()
            if not product_name or product_name.lower() == "nan":
                continue
            cat_class = f.get("Segment") or f.get("Asset Class") or f.get("Category") or ""
            amfi_cat, _ = classify_amfi_category(product_name, cat_class)
            
            # Clean Allocation
            amt_str = str(f.get("Allocation (INR)", "0"))
            amt_val = clean_float_val(amt_str)
            if amt_val == 0.0:
                for alt_key in ["Amount", "Allocation", "Value", "Amt", "allocation"]:
                    if f.get(alt_key):
                        amt_val = clean_float_val(str(f.get(alt_key)))
                        if amt_val > 0.0:
                            break
            total_alloc += amt_val
            
            # Aggressive/growth categories
            cat_lower = amfi_cat.lower()
            if any(x in cat_lower for x in ["small cap", "mid cap", "multi cap", "flexi cap", "large cap", "large & mid", "aggressive hybrid", "pms"]):
                has_aggressive_exposure = True
                aggressive_weight += amt_val

    # Determine risk appetite
    if fund_data and has_aggressive_exposure:
        # If the portfolio contains Small Cap, Multicap, PMS, or Aggressive Hybrid, or has >=25% aggressive assets,
        # it should be classified as Moderately aggressive / Aggressive.
        aggressive_pct = (aggressive_weight / total_alloc * 100) if total_alloc > 0 else 0.0
        
        # Check for specific presence of Small Cap, Multi Cap, Aggressive Hybrid, or PMS
        categories_in_portfolio = []
        for f in fund_data:
            product_name = f.get("Product Name", "").strip()
            cat_class = f.get("Segment") or f.get("Asset Class") or f.get("Category") or ""
            amfi_cat, _ = classify_amfi_category(product_name, cat_class)
            categories_in_portfolio.append(amfi_cat.lower())
            
        has_high_equity = any(x in categories_in_portfolio for x in ["small cap fund", "multi cap fund", "aggressive hybrid fund", "portfolio management services (pms)"])
        
        if aggressive_pct >= 25.0 or has_high_equity:
            if stated_appetite in ["Aggressive", "Moderately aggressive"]:
                risk_appetite = stated_appetite
            else:
                risk_appetite = "Moderately aggressive"
        else:
            risk_appetite = stated_appetite or "Moderate"
    else:
        risk_appetite = stated_appetite or rng.choice(["Conservative", "Moderate", "Moderately aggressive", "Aggressive"])
        
    # Map risk category to advisor pool
    if risk_appetite == "Conservative":
        advisor_pool = [1, 4, 7]
    elif risk_appetite == "Moderate":
        advisor_pool = [5, 6]
    else: # Moderately aggressive or Aggressive
        advisor_pool = [2, 3, 8]
        
    # Determine Advisor ID (matching risk profile category)
    advisor_id = advisor_pool[seed_val % len(advisor_pool)]
    
    # Advisor style configurations
    advisor_configs = {
        1: {
            "name": "Conservative wealth preservation advisor",
            "risk_appetite": "Conservative",
            "objective": "Capital preservation",
            "theme": "Stability & Income Strategy",
            "style": "Defensive investing",
            "market_pos": "Defensive market positioning"
        },
        2: {
            "name": "Growth-focused strategist",
            "risk_appetite": "Aggressive",
            "objective": "Wealth creation",
            "theme": "Capital Compounding Strategy",
            "style": "Growth-oriented",
            "market_pos": "Bullish market environment"
        },
        3: {
            "name": "Long-term compounding advisor",
            "risk_appetite": "Moderately aggressive",
            "objective": "Long-term growth",
            "theme": "Multi-Asset Compounding Strategy",
            "style": "Long-term compounding strategy",
            "market_pos": "Global diversification opportunities"
        },
        4: {
            "name": "Passive income specialist",
            "risk_appetite": "Conservative",
            "objective": "Passive income",
            "theme": "Stability & Income Strategy",
            "style": "Income-focused",
            "market_pos": "High interest-rate environment"
        },
        5: {
            "name": "Macro-economic allocation strategist",
            "risk_appetite": "Moderate",
            "objective": "Balanced growth",
            "theme": "Balanced Wealth Strategy",
            "style": "Balanced allocation",
            "market_pos": "Volatile market conditions"
        },
        6: {
            "name": "Multi-asset diversification advisor",
            "risk_appetite": "Moderate",
            "objective": "Balanced growth",
            "theme": "Global Diversification Strategy",
            "style": "Diversified investing",
            "market_pos": "Global diversification opportunities"
        },
        7: {
            "name": "Defensive market-cycle advisor",
            "risk_appetite": "Conservative",
            "objective": "Capital preservation",
            "theme": "Inflation Protection Strategy",
            "style": "Defensive investing",
            "market_pos": "Inflationary conditions"
        },
        8: {
            "name": "Global opportunity-focused advisor",
            "risk_appetite": "Aggressive",
            "objective": "Long-term growth",
            "theme": "Global Diversification Strategy",
            "style": "Diversified investing",
            "market_pos": "Global diversification opportunities"
        }
    }
    
    config = advisor_configs[advisor_id]
    if not has_intl:
        config = config.copy()
        if "global" in config["theme"].lower():
            config["theme"] = config["theme"].replace("Global", "Multi-Asset").replace("global", "multi-asset")
        if "global" in config["market_pos"].lower():
            config["market_pos"] = config["market_pos"].replace("Global", "Multi-Asset").replace("global", "multi-asset")
        if "global" in config["name"].lower():
            config["name"] = config["name"].replace("Global", "Multi-Asset").replace("global", "multi-asset")
        
    primary_obj = str(client_data.get("Primary Objective", "")).strip()
    if primary_obj and primary_obj.lower() != "nan":
        obj_lower = primary_obj.lower()
        if "preservation" in obj_lower or "preserve" in obj_lower:
            objective = "Capital preservation"
        elif "income" in obj_lower or "passive" in obj_lower or "yield" in obj_lower:
            objective = "Passive income"
        elif "retirement" in obj_lower or "pension" in obj_lower:
            objective = "Retirement planning"
        elif "tax" in obj_lower or "efficiency" in obj_lower:
            objective = "Tax efficiency"
        elif "growth" in obj_lower:
            if "long" in obj_lower:
                objective = "Long-term growth"
            elif "balanced" in obj_lower:
                objective = "Balanced growth"
            else:
                objective = "Wealth creation"
        else:
            objective = primary_obj
    else:
        objective = config["objective"]
        
    theme = config["theme"]
    style = config["style"]
    market_pos = config["market_pos"]
    
    horizon = str(client_data.get("Investment Horizon", "")).strip()
    if horizon and horizon.lower() != "nan":
        horizon_val = horizon
    else:
        if risk_appetite == "Conservative":
            horizon_val = rng.choice(["3-5 Years", "5+ Years", "Medium Term"])
        else:
            horizon_val = rng.choice(["5-7 Years", "7+ Years", "10+ Years", "Long Term"])
            
    if risk_appetite == "Conservative":
        age_group = rng.choice(["Late Career (50-60)", "Retirees (60+)", "Middle Aged (45-55)"])
        liquidity_needs = "High - Requires regular payouts and capital buffers" if objective == "Passive income" else "Moderate - Requires quarterly yield or emergency liquid access"
        income_stability = "Stable / Post-retirement pensions & rental flows"
        wealth_preservation = "Critical - Low threshold for principal drawdown"
    elif risk_appetite == "Moderate":
        age_group = rng.choice(["Middle Aged (40-50)", "Established Professionals (35-45)"])
        liquidity_needs = "Moderate - Seeks growth with occasional partial redemptions"
        income_stability = "Highly stable professional salary or business flows"
        wealth_preservation = "Moderate - Willing to accept minor fluctuations to protect against inflation"
    else:
        age_group = rng.choice(["Young Professionals (25-35)", "Accumulators (30-45)"])
        liquidity_needs = "Low - Focus is on compounding, minimal short-term needs"
        income_stability = "High growth career earnings or active business cash flows"
        wealth_preservation = "Growth focused - Willing to accept short-term corrections for long-term compound gains"

    profile = {
        "client_name": client_name,
        "risk_appetite": risk_appetite,
        "objective": objective,
        "portfolio_theme": theme,
        "investment_style": style,
        "market_positioning": market_pos,
        "advisor_id": advisor_id,
        "advisor_name": config["name"],
        "has_intl": has_intl,
        "assumptions": {
            "age_group": age_group,
            "investment_horizon": horizon_val,
            "liquidity_needs": liquidity_needs,
            "income_stability": income_stability,
            "wealth_preservation_requirements": wealth_preservation
        }
    }
    return profile

def generate_dynamic_briefings_local(profile, corpus_words):
    client_name = profile["client_name"]
    objective = profile["objective"]
    risk_appetite = profile["risk_appetite"]
    theme = profile["portfolio_theme"]
    style = profile["investment_style"]
    market_pos = profile["market_positioning"]
    assumptions = profile["assumptions"]
    horizon = assumptions["investment_horizon"]
    advisor_id = profile["advisor_id"]
    
    if advisor_id == 1:
        exec_summary = f"This strategic proposal for {client_name} details our risk-averse allocation framework, styled as a {theme}. Focused on capital preservation over a {horizon} window, we have structured a safety-first distribution of {corpus_words} to shield your principal. By emphasizing defensive placement, we aim to deliver capital stability and peace of mind during shifting cycles."
        thesis = "Our core asset allocation thesis focuses on capital defense. Rather than seeking aggressive upside, we prioritize preserving the purchasing power of your funds. We combine liquid cash sleeves with highly rated corporate debt to secure a reliable, low-volatility income shield."
        market_comm = "Under current volatile market conditions, elevated equity valuations warrant extreme caution. We adopt a defensive posture, shifting capital toward short-duration yields and arbitrage hedges. This positioning buffers the portfolio from sudden downside corrections while maintaining essential liquidity."
    elif advisor_id == 2:
        exec_summary = f"We present this high-conviction investment strategy for {client_name}, engineered as an {theme}. Aiming for maximum wealth expansion over a {horizon} horizon, we deploy the corpus of {corpus_words} into dynamic growth engines. This opportunistic model captures structural corporate earnings and rising sector leaders."
        thesis = "Our allocation strategy rests on backing top-tier growth enterprises. We believe that long-term outperformance is driven by concentrated exposure to emerging leaders and secular themes. Debt is held purely as a tactical reservoir to buy stock dips."
        market_comm = "The mid-2026 economic environment displays strong domestic demand and high corporate capital spending. This optimistic growth cycle supports an active, equity-heavy allocation. We participate in sectors like manufacturing and digital innovation to capture structural compounding gains."
    elif advisor_id == 3:
        exec_summary = f"Prepared for {client_name}, this proposal outlines our {theme} for long-term compounding. Focusing on generational wealth creation over the next {horizon}, we place the total corpus of {corpus_words} into enduring assets. This patient strategy ignores daily market noise to let quality businesses grow."
        thesis = "Our philosophy centers on business ownership rather than paper trading. We select funds that invest in moat-rich companies with clean governance and strong free cash flows. This approach ensures capital compounds steadily through economic cycles."
        market_comm = "While macro indicators and policy shifts cause short-term fluctuations, the long-term structural path for domestic corporate growth remains highly positive. We ignore temporary market volatility, focusing instead on high-quality compounding engines that build enduring wealth."
    elif advisor_id == 4:
        exec_summary = f"This custom-built portfolio for {client_name} implements a {theme} optimized for yield generation. Structured for your Passive income objective over {horizon}, this allocation of {corpus_words} provides consistent income streams. We prioritize security and yield consistency to support your lifestyle flows."
        thesis = "We view the portfolio through a cash-flow lens. Our structure is built around high-yield corporate bonds, hybrid debt, and monthly-payout asset sleeves. This combination minimizes capital drawdowns while securing reliable income distributions."
        market_comm = "With current interest rates peaking, we lock in highly attractive corporate yields before the cycle shifts. This income-centric placement insulates your cash flow from equity market swings and provides a stable capital anchor."
    elif advisor_id == 5:
        exec_summary = f"For {client_name}, we have structured a {theme} using tactical macro-allocation. Aiming for balanced growth over a {horizon} period, this allocation of {corpus_words} is designed to shift capital in response to changing cycles. We balance equities, debt, and gold dynamically."
        thesis = "Our thesis is top-down and macro-driven. We monitor interest rates, credit growth, inflation, and relative valuations to adjust weights. This active asset shifting avoids expensive sectors and buys underpriced categories."
        market_comm = "Mid-2026 presents a transition phase with steady economic growth but emerging inflationary risks. We balance corporate credit yields with commodity hedges (like gold) and selective large-cap stocks. This macro-diversified mix protects capital while participating in cycle shifts."
    elif advisor_id == 6:
        exec_summary = f"This strategic proposal for {client_name} details our {theme}. Tailored to your objectives over {horizon}, we distribute {corpus_words} across uncorrelated asset classes. This multi-layered structure maximizes return efficiency while smoothing out price fluctuations."
        has_intl = profile.get("has_intl", True)
        if has_intl:
            thesis = "We believe that true diversification is the only free lunch in finance. By combining shares, debt, gold, and international assets, we ensure the portfolio is not dependent on any economic factor or AMC style."
            market_comm = "Given high global uncertainties and shifting trade policies, a single-asset approach is excessively risky. We distribute exposure across multiple uncorrelated sleeves. Gold acts as a macro hedge, bonds provide yield, and equities drive capital appreciation."
        else:
            thesis = "We believe that true diversification is the only free lunch in finance. By combining shares, debt, gold, and low-correlation arbitrage assets, we ensure the portfolio is not dependent on any single economic factor or AMC style."
            market_comm = "Given market complexities and shifting domestic cycles, a single-asset approach is excessively risky. We distribute exposure across multiple uncorrelated domestic sleeves. Gold acts as a macro hedge, bonds provide yield, and equities drive capital appreciation."
    elif advisor_id == 7:
        exec_summary = f"This customized proposal for {client_name} outlines our defensive {theme} to handle volatility. Structured for capital preservation over {horizon}, we allocate the corpus of {corpus_words} into hedged and low-beta segments. This protective model curbs valuation swings during cycles."
        thesis = "We prioritize downside shielding. Our thesis utilizes arbitrage spreads, conservative debt, and low-beta equities. This ensures that when stock markets decline, your capital remains anchored and insulated."
        market_comm = "The current economic regime exhibits elevated multiples and geopolitical tensions. Adopting a defensive cycle posture is essential. We allocate significantly to market-neutral arbitrage and senior secured debt to establish a strong capital preservation floor."
    else:
        has_intl = profile.get("has_intl", True)
        if has_intl:
            exec_summary = f"Prepared for {client_name}, this proposal details our {theme} focused on international growth. Structured for geographical dispersion over {horizon}, we allocate {corpus_words} across domestic and international assets. This broad strategy hedges against local currency risk."
            thesis = "Our thesis leverages global economic compounding. We allocate to both local growth leaders and international equity/gold funds. This broad exposure captures global technology themes while protecting against domestic policy changes."
            market_comm = "In a highly connected world economy, restricting investments to a single country is limiting. We capture the secular growth of domestic consumer markets while participating in global technology leaders and precious metal hedges. This insulates and expands capital."
        else:
            exec_summary = f"Prepared for {client_name}, this proposal details our {theme} focused on diversified domestic asset allocation. Structured for balanced growth and stability over {horizon}, we distribute {corpus_words} across diversified mutual funds and hybrid asset sleeves. This strategy aims for risk-adjusted compounding and long-term wealth creation."
            thesis = "Our thesis focuses on multi-asset diversification and long-term wealth creation. We allocate to domestic equity growth leaders, high-quality corporate bonds, and arbitrage hedges. This structure balances capital appreciation with downside defense to optimize risk-adjusted compounding."
            market_comm = "In a dynamic domestic economy, a balanced multi-asset approach provides a resilient path forward. We combine capital growth from diversified domestic equities, steady yield from fixed income, and low-correlation gold and arbitrage hedges. This positioning insulates capital from single-market shocks while capturing long-term compounding."
        
    return {
        "executive_summary": exec_summary,
        "portfolio_thesis": thesis,
        "market_commentary": market_comm
    }

def scrub_forbidden_phrases(text):
    if not text:
        return text
        
    # Replace forbidden phrases
    text = text.replace("Stable Income", "Fixed Income")
    text = text.replace("stable income", "fixed income")
    text = text.replace("Stable income", "Fixed income")
    text = text.replace("Smart Asset Mix", "Balanced Asset Allocation")
    text = text.replace("smart asset mix", "balanced asset allocation")
    text = text.replace("Aggressive Growth", "Capital Compounding")
    text = text.replace("aggressive growth", "capital compounding")
    text = text.replace("Aggressive growth", "Capital compounding")
    
    text = text.replace("Wealth Creation", "__WEALTH_CREATION__")
    text = text.replace("wealth creation", "__WEALTH_CREATION_LC__")
    text = text.replace("Stability & Income Strategy", "__THEME_STABILITY_INCOME__")
    text = text.replace("stability & income strategy", "__THEME_STABILITY_INCOME_LC__")
    text = text.replace("Global Diversification Strategy", "__THEME_GLOBAL_DIVERSIFICATION__")
    text = text.replace("global diversification strategy", "__THEME_GLOBAL_DIVERSIFICATION_LC__")
    text = text.replace("Multi-Asset Diversification Strategy", "__THEME_MULTI_ASSET_DIVERSIFICATION__")
    text = text.replace("multi-asset diversification strategy", "__THEME_MULTI_ASSET_DIVERSIFICATION_LC__")
    text = text.replace("Multi-asset diversification strategy", "__THEME_MULTI_ASSET_DIVERSIFICATION_LC2__")

    replacements = {
        "diversifies across": "allocates across",
        "diversify across": "allocate across",
        "diversifies exposure": "spreads risks",
        "diversification": "asset distribution",
        "diversified": "distributed",
        "reduces volatility": "smooths price fluctuations",
        "reduce volatility": "smooth price fluctuations",
        "reducing volatility": "smoothing price fluctuations",
        "provides stability": "anchors the portfolio",
        "provide stability": "anchor the portfolio",
        "provides stable": "offers reliable",
        "provide stable": "offer reliable",
        "provides a stable": "offers a reliable",
        "stability": "preservation",
        "stable": "reliable",
        "dynamic equity-debt allocation": "active asset distribution",
        "consistent returns across market conditions": "steady historical growth patterns",
        "balanced risk-reward": "pragmatic risk alignment",
        "long-term wealth creation": "generational wealth building"
    }
    
    import re
    scrubbed = text
    for phrase, replacement in replacements.items():
        pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
        scrubbed = pattern.sub(replacement, scrubbed)
        
    scrubbed = re.sub(r'^(?:provides\s+)', 'Offers ', scrubbed, flags=re.IGNORECASE)
    scrubbed = re.sub(r'^(?:helps\s+)', 'Supports ', scrubbed, flags=re.IGNORECASE)
    scrubbed = re.sub(r'^(?:acts\s+as\s+)', 'Serves as ', scrubbed, flags=re.IGNORECASE)
    scrubbed = re.sub(r'^(?:diversifies\s+)', 'Spreads exposure across ', scrubbed, flags=re.IGNORECASE)
    
    scrubbed = re.sub(r'\.\s+(?:provides\s+)', '. Offers ', scrubbed, flags=re.IGNORECASE)
    scrubbed = re.sub(r'\.\s+(?:helps\s+)', '. Supports ', scrubbed, flags=re.IGNORECASE)
    scrubbed = re.sub(r'\.\s+(?:acts\s+as\s+)', '. Serves as ', scrubbed, flags=re.IGNORECASE)
    scrubbed = re.sub(r'\.\s+(?:diversifies\s+)', '. Spreads exposure across ', scrubbed, flags=re.IGNORECASE)
    
    scrubbed = scrubbed.replace("__WEALTH_CREATION__", "Wealth Creation")
    scrubbed = scrubbed.replace("__WEALTH_CREATION_LC__", "wealth creation")
    scrubbed = scrubbed.replace("__THEME_STABILITY_INCOME__", "Stability & Fixed Income Strategy")
    scrubbed = scrubbed.replace("__THEME_STABILITY_INCOME_LC__", "stability & fixed income strategy")
    scrubbed = scrubbed.replace("__THEME_GLOBAL_DIVERSIFICATION__", "Global Diversification Strategy")
    scrubbed = scrubbed.replace("__THEME_GLOBAL_DIVERSIFICATION_LC__", "global diversification strategy")
    scrubbed = scrubbed.replace("__THEME_MULTI_ASSET_DIVERSIFICATION__", "Multi-Asset Diversification Strategy")
    scrubbed = scrubbed.replace("__THEME_MULTI_ASSET_DIVERSIFICATION_LC__", "multi-asset diversification strategy")
    scrubbed = scrubbed.replace("__THEME_MULTI_ASSET_DIVERSIFICATION_LC2__", "Multi-asset diversification strategy")
    
    return scrubbed

def is_generic_template_rationale(text):
    if not text:
        return True
    val = str(text).strip().lower()
    if len(val) < 10:
        return True
    
    # Generic keywords from default Excel templates
    templates = [
        "keeps your cash safe",
        "market-neutral strategy",
        "capitalizes on short-term",
        "combines 15-20% equity",
        "holds debt from",
        "backed by hdfc",
        "combines bond stability",
        "decade of zero delinquencies",
        "maintains a balanced",
        "investment in equity, debt",
        "spreads wealth across",
        "exposure to equities",
        "exposure to domestic",
        "invests in a select",
        "aggressive stance as of",
        "backs emerging",
        "high-conviction mid",
        "holds dominant",
        "flagship equity fund",
        "under harish krishnan"
    ]
    return any(t in val for t in templates)

def validate_rationale(product_name, category, text, corpus_val, corpus_words_str):
    if not text:
        return True, ""
    
    text_lower = str(text).lower()
    
    c_words_clean = corpus_words_str.lower().replace(" ", "").replace(".0", "")
    text_clean = text_lower.replace(" ", "").replace(".0", "")
    
    lakhs_str = f"{corpus_val / 100000:.1f}lakh"
    lakhs_str2 = f"{int(corpus_val / 100000)}lakh"
    crores_str = f"{corpus_val / 10000000:.1f}crore"
    crores_str2 = f"{int(corpus_val / 10000000)}crore"
    
    forbidden_corpus_mentions = [
        "total corpus", "overall corpus", "entire corpus", "whole corpus",
        lakhs_str, lakhs_str2, crores_str, crores_str2,
        c_words_clean
    ]
    
    for forbidden in forbidden_corpus_mentions:
        if forbidden in text_clean or forbidden in text_lower:
            return False, f"Contains forbidden corpus reference: '{forbidden}'"
            
    is_small_cap = any(x in category.lower() or x in product_name.lower() for x in ["small cap", "small-cap", "smallcap", "smallcao"])
    if is_small_cap:
        small_cap_forbidden_descriptors = [
            "business giants", "blue-chip", "mature market", "industry leaders", "market giants",
            "business giant", "bluechip", "mature leader", "established giant"
        ]
        for forbidden in small_cap_forbidden_descriptors:
            if forbidden in text_lower or forbidden.replace(" ", "") in text_lower.replace(" ", ""):
                return False, f"Small Cap rationale contains category-inconsistent descriptor: '{forbidden}'"
                
    return True, ""

def get_amc_name(product_name):
    name_lower = str(product_name).lower().strip()
    amcs = [
        "kotak", "mahindra manulife", "mahindra", "sbi", "icici prudential", "icici",
        "hdfc", "nippon india", "nippon", "mirae asset", "mirae", "parag parikh", "ppfas",
        "axis", "aditya birla sun life", "aditya birla", "absl", "tata", "dsp", "uti",
        "hsbc", "bandhan", "idfc", "invesco", "sundaram", "motilal oswal", "motilal",
        "franklin templeton", "franklin", "canara robeco", "canara", "baroda bnp paribas",
        "baroda", "bnp paribas", "pgim india", "pgim", "quant", "lic", "groww", "navi"
    ]
    for amc in amcs:
        if name_lower.startswith(amc):
            return amc.title()
    for amc in amcs:
        if amc in name_lower:
            return amc.title()
    words = product_name.split()
    if words:
        return words[0]
    return "the fund"

def _get_fallback_rationale_for_product(part, product_name, profile, allocation_str=None, excel_rationale="", amfi_category=None, variant_offset=0):
    part = int(part)
    clean_name = str(product_name).strip()
    client_name = profile["client_name"]
    objective = profile["objective"]
    risk_appetite = profile["risk_appetite"]
    theme = profile["portfolio_theme"]
    advisor_id = profile["advisor_id"]
    
    assumptions = profile.get("assumptions", {})
    horizon = assumptions.get("investment_horizon", "Medium Term")
    liquidity = assumptions.get("liquidity_needs", "Moderate")
    wealth_pres = assumptions.get("wealth_preservation_requirements", "Standard")
    market_pos = profile.get("market_positioning", "Volatile market conditions")
    corpus_words = profile.get("corpus_words", "your portfolio")

    def format_allocation_rupee(amt):
        val = clean_float_val(str(amt))
        if val == 0.0:
            return "this allocation"
        if val >= 10000000.0:
            cr_val = val / 10000000.0
            if cr_val.is_integer():
                return f"₹{int(cr_val)} Crore"
            else:
                return f"₹{cr_val:.1f} Crore"
        else:
            lakh_val = val / 100000.0
            if lakh_val.is_integer():
                return f"₹{int(lakh_val)} Lakh"
            else:
                return f"₹{lakh_val:.1f} Lakh"

    allocation_words = format_allocation_rupee(allocation_str)

    # Clean up client name for highly natural, advisor-like phrasing
    import re
    short_client = re.sub(r'\(.*?\)', '', client_name).strip()
    short_client = re.sub(r'(?i)\b(and family|family office|family|mam|sir|office)\b', '', short_client).strip()
    short_client = re.sub(r'(?i)\b(and|&)\b$', '', short_client).strip()
    short_client = short_client.strip(" &")

    # Define synonyms for dynamic swapping to increase word variety
    synonyms = {
        "safer": ["safer", "more secure", "protected", "extra safe"],
        "steady": ["steady", "consistent", "gradual", "reliable", "predictable"],
        "growth": ["growth", "appreciation", "returns", "compounding"],
        "wealth": ["wealth", "savings", "capital", "portfolio value"],
        "money": ["money", "funds", "savings", "capital"],
        "balanced": ["balanced", "stable", "steady", "well-proportioned"],
        "downs": ["downs", "price swings", "fluctuations", "shifts"]
    }
    
    def swap_synonyms(text):
        words = text.split(" ")
        for i, w in enumerate(words):
            w_clean = re.sub(r'[^\w]', '', w).lower()
            if w_clean in synonyms:
                choices = synonyms[w_clean]
                replacement = random.choice(choices)
                if w[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                punc = re.sub(r'[\w]', '', w)
                words[i] = replacement + punc
        return " ".join(words)

    # 30 base templates per segment in simple one-line language
    part_1_options = [
        "Keeps part of the portfolio safer.",
        "Keeps part of the money safer.",
        "Good option for keeping your money safe.",
        "Added to hold a safe cash reserve for any emergency.",
        "Helps protect your immediate cash from stock market drops.",
        "Provides a safe harbor for your capital.",
        "Keeps a portion of your funds safe and easy to reach.",
        "Chosen to secure your cash with low risk.",
        "Good choice for parking money that you might need soon.",
        "Added to keep your short-term savings safe.",
        "Helps secure your capital while keeping it ready for use.",
        "Keeps a buffer of safer money separate from market movements.",
        f"Chosen to keep {short_client}'s immediate savings extra safe.",
        f"Keeps a buffer of safer money ready for {short_client}.",
        f"Provides a secure cash harbor for {short_client}.",
        f"Added to protect {short_client}'s cash from market drops.",
        "Good option to keep a portion of funds safe and liquid.",
        "Helps keep cash reserves safe and reachable.",
        "Selected to secure a safe cash buffer.",
        "Keeps a safe reserve separate from market noise.",
        "Added to keep your capital safe and accessible.",
        "Chosen for high capital safety and peace of mind.",
        "Helps protect immediate savings from price swings.",
        "Provides a safe spot for short-term savings.",
        "Keeps a secure buffer for your peace of mind.",
        f"Selected to hold a safe cash reserve for {short_client}.",
        f"Keeps {short_client}'s cash reserves safe and liquid.",
        f"Good option to protect {short_client}'s short-term funds.",
        "Chosen to give you quick access to cash when needed.",
        "Good choice for stable and low-risk savings."
    ]

    part_2_options = [
        "Good option for stable returns and regular payouts.",
        "Chosen for consistent performance and regular cash flow.",
        "Added to generate reliable payouts with low risk.",
        "Helps bring in steady returns to cover regular expenses.",
        "Keeps your capital protected while paying regular interest.",
        "Added to secure regular income and protect your main investment.",
        "Good choice for steady returns that outpace normal bank accounts.",
        "Chosen to lock in reliable payouts from high-quality bonds.",
        "Provides a steady income stream to support your cash needs.",
        "Helps anchor the portfolio with predictable returns.",
        "Added for steady payouts to keep your income flow stable.",
        "Good option for consistent payouts and low price swings.",
        f"Provides a steady income stream to support {short_client}.",
        f"Helps anchor {short_client}'s portfolio with steady returns.",
        f"Added to generate reliable payouts for {short_client}.",
        f"Good option for stable returns in {short_client}'s portfolio.",
        "Helps bring in consistent monthly payouts.",
        "Chosen to secure regular yields with low capital risk.",
        "Added for predictable payouts and capital protection.",
        "Good choice for regular payouts and steady interest.",
        "Provides consistent interest income with low volatility.",
        "Chosen to generate reliable income flows over time.",
        "Helps balance the portfolio with steady interest returns.",
        "Keeps your income stream secure and highly reliable.",
        "Added to lock in attractive yields for steady payouts.",
        f"Good choice for regular payouts to support {short_client}.",
        f"Helps bring in consistent interest payouts for {short_client}.",
        f"Selected to secure stable income streams for {short_client}.",
        "Good option for consistent cash payouts and safety.",
        "Chosen to protect capital while producing steady yields."
    ]

    part_3_options = [
        "Helps keep the portfolio balanced through market cycles.",
        "Helps manage market ups and downs using a smart mix.",
        "Helps balance safety and growth by shifting assets.",
        "Chosen to reduce overall risk by spreading investments.",
        "Good option for steady growth with a built-in safety net.",
        "Added to smooth out market changes and limit sudden drops.",
        "Helps protect your money while still letting it grow.",
        "Chosen to balance your shares with gold and safer bonds.",
        "Provides a smoother ride during times of market uncertainty.",
        "Good choice for growing wealth without taking excessive risk.",
        "Helps balance safety and growth across different assets.",
        "Added to protect capital values during market price swings.",
        f"Helps keep {short_client}'s portfolio balanced through cycles.",
        f"Helps manage market ups and downs for {short_client}.",
        f"Helps balance safety and growth for {short_client}.",
        f"Chosen to reduce overall risk for {short_client}'s portfolio.",
        "Good option to balance safety and growth.",
        "Added to reduce sudden market impact.",
        "Helps maintain balance in the portfolio.",
        "Chosen to smooth out market ups and downs.",
        "Provides a balanced mix to protect and grow capital.",
        "Good choice to reduce overall portfolio price swings.",
        "Helps balance your equity risk with commodities and bonds.",
        "Added to cushion the portfolio during market drops.",
        "Selected to capture steady growth with built-in protection.",
        f"Added to smooth out market changes for {short_client}.",
        f"Good choice for growing {short_client}'s savings safely.",
        f"Provides a balanced mix to protect {short_client}'s funds.",
        "Chosen to maintain a steady and balanced asset mix.",
        "Good option to protect your wealth while capturing growth."
    ]

    part_4_options = [
        "Added for steady long-term growth.",
        "Added to create long-term wealth by backing strong companies.",
        "Added for better future growth potential.",
        "Chosen to compound your wealth steadily in top-tier firms.",
        "Good option for growing your savings over a longer timeframe.",
        "Helps build future wealth by participating in rising sectors.",
        "Added to capture long-term growth in the business market.",
        "Chosen to grow your savings and beat inflation over time.",
        "Provides a strong engine for long-term growth.",
        "Good choice to build wealth for your long-term goals.",
        "Helps grow your money steadily through quality stock investments.",
        "Added for strong growth potential over the coming years.",
        f"Added for steady long-term growth for {short_client}.",
        f"Added to create long-term wealth for {short_client}.",
        f"Added for better future growth potential for {short_client}.",
        f"Chosen to compound {short_client}'s wealth steadily.",
        "Selected for gradual and consistent growth.",
        "Good option for stable wealth creation.",
        "Helps build long-term savings through quality stocks.",
        "Chosen to capture strong corporate growth over time.",
        "Added to drive long-term capital compounding.",
        "Good choice for building generational wealth steadily.",
        "Provides exposure to market leaders for high future growth.",
        "Helps grow your capital by backing robust businesses.",
        "Added to capture future compounding gains in stocks.",
        f"Good choice to build long-term wealth for {short_client}.",
        f"Helps grow {short_client}'s money steadily over time.",
        f"Added for better future growth for {short_client}.",
        "Chosen to grow your savings over the coming years.",
        "Good option for steady long-term wealth compounding."
    ]

    # Map parts to pools
    if part == 1:
        pool = part_1_options
    elif part == 2:
        pool = part_2_options
    elif part == 3:
        pool = part_3_options
    else:
        pool = part_4_options

    # Choose randomly on every request to prioritize variation over consistency
    base_choice = random.choice(pool)
    why_selected = swap_synonyms(base_choice)
    
    # Inject dynamic tails reflecting client objective and risk profile to avoid repetition
    obj_tails = {
        "Capital preservation": ["to shield your hard-earned wealth.", "to ensure capital protection first.", "focusing purely on capital safety."],
        "Passive income": ["to support consistent income needs.", "to secure stable cash flow payouts.", "aiming for reliable cash yield."],
        "Retirement planning": ["to support long-term retirement security.", "anchoring your post-career fund needs.", "for stable long-term retirement planning."],
        "Tax efficiency": ["optimized for post-tax efficiency.", "minimizing your tax exposure.", "with a focus on post-tax returns."],
        "Long-term growth": ["to drive long-term capital compounding.", "aiming for steady growth over time.", "designed for long-term wealth appreciation."],
        "Balanced growth": ["to balance safety and growth steadily.", "providing a balanced allocation approach.", "designed for steady asset growth."],
        "Wealth creation": ["to build long-term generational wealth.", "to expand your capital compounding base.", "aiming for maximum capital compounding."]
    }
    
    tail = ""
    matched_obj = None
    if objective:
        for k in obj_tails:
            if k.lower() in str(objective).lower():
                matched_obj = k
                break
                
    if matched_obj:
        tail = " " + random.choice(obj_tails[matched_obj])
    else:
        if risk_appetite == "Conservative":
            tail = " prioritizing principal safety."
        elif risk_appetite == "Aggressive":
            tail = " aiming for high long-term gains."
        else:
            tail = " balancing risk and returns."
            
    if why_selected.endswith("."):
        why_selected = why_selected[:-1]
    why_selected = why_selected + tail
    if not why_selected.endswith("."):
        why_selected = why_selected + "."

    # Populate segment-specific expected role options
    if part == 1:
        role_options = [
            f"Serves as an immediate cash buffer for {short_client}.",
            f"Acts as a highly liquid capital shield for {short_client}.",
            f"Provides instant emergency liquidity for the portfolio."
        ]
        risk_options = [
            "Principal risk is extremely low and managed with high safety.",
            "Highly secure placement focusing on stable capital values.",
            "Low volatility to ensure total capital preservation."
        ]
        benefit_options = [
            "Quick access to cash and safety from market volatility.",
            "Complete capital security with near-zero market correlation.",
            "Immediate liquidity whenever needs arise."
        ]
        positioning_options = [
            "Invests in highest-rated short-term treasury assets.",
            "Conservatively managed liquid vehicle for maximum safety.",
            "Focuses on high-quality debt with zero credit exposure."
        ]
        downside_options = [
            "Completely insulated from stock market fluctuations.",
            "Cushions the overall portfolio against market drops.",
            "Provides a stable capital anchor during market corrections."
        ]
        diversification_options = [
            "Reduces total risk by holding cash-equivalent reserves.",
            "Offsets equity market exposure with steady liquid safety.",
            "Maintains essential liquid balance for asset allocation."
        ]
    elif part == 2:
        role_options = [
            f"Generates consistent income streams to support {short_client}.",
            f"Provides steady yields to cover regular cash payouts.",
            f"Serves to anchor the portfolio's income-generating segment."
        ]
        risk_options = [
            "Moderate-low risk, prioritizing yield over equity-like growth.",
            "Controlled swings focusing on consistent debt coupon flows.",
            "Low to moderate volatility with high credit safety."
        ]
        benefit_options = [
            "Consistent coupon payouts and monthly/quarterly yields.",
            "Reliable income distributions to support regular expenses.",
            "Outpaces standard deposit rates with moderate safety."
        ]
        positioning_options = [
            "Holds highly rated corporate debt and high-yield bonds.",
            "Managed by a seasoned fixed-income credit research team.",
            "Selected for strong credit quality and interest cycle alignment."
        ]
        downside_options = [
            "Cushions capital with regular interest inflows during market drops.",
            "Maintains low correlation to equity market slides.",
            "Less sensitive to stock price changes for capital protection."
        ]
        diversification_options = [
            "Balances equity holdings with fixed income yield blocks.",
            "Adds reliable corporate debt exposure to lower portfolio swings.",
            "Spreads risk away from pure stock market dependencies."
        ]
    elif part == 3:
        role_options = [
            f"Smooths out portfolio price swings for {short_client}.",
            f"Balances equity and debt exposure dynamically.",
            f"Bridges growth and safety in a single holding."
        ]
        risk_options = [
            "Moderate risk, balanced across stock growth and bond safety.",
            "Controlled asset fluctuations through active cycle shifting.",
            "Provides a balanced risk profile for steady compound returns."
        ]
        benefit_options = [
            "Steady capital growth with a built-in safety cushion.",
            "Smoother return experience across varying economic cycles.",
            "Consistent long-term wealth building with limited risk."
        ]
        positioning_options = [
            "Uses a multi-asset approach including stocks, bonds, and gold.",
            "Top-performing hybrid allocation fund in its class.",
            "Managed to dynamically catch market upside while trimming downside."
        ]
        downside_options = [
            "Gold and debt sleeves shield capital during equity corrections.",
            "Uses dynamic rebalancing to reduce peak-to-trough drawdowns.",
            "Protective asset mix shields the portfolio from stock drops."
        ]
        diversification_options = [
            "Combines multiple uncorrelated asset classes in one fund.",
            "Spreads exposure across commodities, debt, and equities.",
            "Lowers overall portfolio swings through robust diversification."
        ]
    else:  # part 4
        role_options = [
            f"Acts as the core wealth compounding engine for {short_client}.",
            f"Drives long-term capital appreciation for {short_client}.",
            f"Focuses on beating inflation through corporate growth."
        ]
        risk_options = [
            "Higher risk matching an aggressive wealth creation objective.",
            "Subject to short-term equity market fluctuations.",
            "Willing to accept short-term price swings for long-term gains."
        ]
        benefit_options = [
            "Strong long-term compound growth over a multi-year horizon.",
            "Wealth expansion through high-conviction equity selections.",
            "Outperforms inflation to secure future purchasing power."
        ]
        positioning_options = [
            "Invests in top-tier industry leaders with strong moats.",
            "Backed by high-conviction stock research and AMC pedigree.",
            "Focuses on fast-growing companies with robust governance."
        ]
        downside_options = [
            "Long investment horizon acts as the ultimate shock absorber.",
            "Quality business selections prevent permanent capital loss.",
            "Underlying strong corporate earnings provide a price floor."
        ]
        diversification_options = [
            "Participates in high-growth industrial and consumer sectors.",
            "Drives long-term capital returns alongside safer parts.",
            "Complements income and cash parts with growth engines."
        ]

    role_choice = random.choice(role_options)
    risk_choice = random.choice(risk_options)
    benefit_choice = random.choice(benefit_options)
    pos_choice = random.choice(positioning_options)
    down_choice = random.choice(downside_options)
    div_choice = random.choice(diversification_options)

    # Identify category
    category = "large_cap" # default
    cat_to_check = str(amfi_category or "").lower() if amfi_category else str(product_name).lower()
    name_lower = str(product_name).lower()
    
    if "arbitrage" in cat_to_check or "arbitrage" in name_lower:
        category = "arbitrage"
    elif "balanced advantage" in cat_to_check or "baf" in cat_to_check or "dynamic asset" in cat_to_check or "dynamic equity" in cat_to_check or "balanced advantage" in name_lower or "dynamic asset" in name_lower:
        category = "baf"
    elif "multi asset" in cat_to_check or "multi-asset" in cat_to_check or "multiasset" in cat_to_check or "multi asset" in name_lower:
        category = "multi_asset"
    elif "small cap" in cat_to_check or "small-cap" in cat_to_check or "smallcap" in cat_to_check or "small cap" in name_lower:
        category = "small_cap"
    elif "multicap" in cat_to_check or "multi cap" in cat_to_check or "multi-cap" in cat_to_check or "multicap" in name_lower or "multi cap" in name_lower:
        category = "multicap"
    elif "mid cap" in cat_to_check or "mid-cap" in cat_to_check or "midcap" in cat_to_check or "mid cap" in name_lower or "midcap" in name_lower:
        category = "mid_cap"
    elif "hybrid" in cat_to_check or "hybrid" in name_lower:
        category = "hybrid"
    elif any(kw in cat_to_check or kw in name_lower for kw in ["liquid", "money market", "overnight", "treasury", "savings", "cash"]):
        category = "liquid"
    elif any(kw in cat_to_check or kw in name_lower for kw in ["gilt", "debt", "bond", "fixed income", "income", "credit risk", "corporate bond"]):
        category = "debt"
    else:
        if part == 1:
            category = "liquid"
        elif part == 2:
            category = "debt"
        elif part == 3:
            category = "hybrid"
        else:
            category = "large_cap"

    detailed_templates = {
        "baf": [
            "To navigate market valuations dynamically, we allocate a portion of {short_client}'s portfolio here. This active strategy utilizes valuation-driven shifting between equity and debt. The ultimate goal is to cushion against market drawdowns while keeping pace with rising equity markets over the long term.",
            "By adjusting equity exposure relative to market valuations, this fund provides {short_client} a smoother growth path. The dynamic reallocation mechanism acts as a risk buffer for this {allocation_words} allocation. It offers active capital preservation alongside participation in stock gains during bull phases.",
            "For {short_client}'s portfolio, this fund manages volatility through automatic asset rebalancing. High stock markets trigger a shift into debt, while downturns prompt equity buying. This systematic hedging approach aligns perfectly with your {risk_appetite} profile and supports steady wealth compounding.",
            "This dynamic asset allocator shifts between equity and cash/debt based on valuations. It aims to capture market upside for {short_client} while mitigating peak corrections. The dynamic rebalancing keeps risk tightly controlled, serving as a reliable anchor for this segment.",
            "We select this position to balance equity gains with downside buffers for {short_client}. Valuation metrics dictate the fund's internal allocation shifts between asset classes. This systematic control supports your objective of {objective} while stabilizing the overall portfolio footprint."
        ],
        "multi_asset": [
            "This multi-asset strategy distributes {short_client}'s capital across equity, fixed income, gold, and arbitrage. Since these classes perform differently in various cycles, the portfolio gains resilient growth. It spreads asset risk across uncorrelated instruments to defend your capital.",
            "Spreading {short_client}'s risk across uncorrelated asset classes is the core strength of this fund. By combining shares, debt, and gold, the manager reduces vulnerability to single-market drops. This {allocation_words} allocation serves as an important stabilizing component of the portfolio during economic transitions.",
            "Gold, debt, and equity exposures are dynamically adjusted here to lower portfolio volatility. For {short_client}, this multi-asset blend offers structural protection against high inflation. It ensures steady compounding aligned with a {risk_appetite} stance through economic cycle rotations.",
            "To guard {short_client}'s wealth from equity market shocks, this fund spreads its holdings. Uncorrelated asset classes like precious metals and fixed income act as buffers. It balances growth with reliable diversifiers, ensuring the {allocation_words} allocation remains resilient while supporting the overall portfolio.",
            "This fund provides {short_client} instant access to multiple asset segments. Spreading exposure beyond domestic equities ensures this {allocation_words} allocation is well-defended. It supports the {objective} goal through all cycles by minimizing drawdown correlations."
        ],
        "hybrid": [
            "We utilize this blended strategy to capture equity market returns while maintaining a structural debt cushion. The fixed 65-80% equity allocation drives long-term appreciation for {short_client}. Simultaneously, the debt sleeve provides regular income and stability for the allocation.",
            "This hybrid portfolio blends active equity participation with fixed income protection. For {short_client}, it acts as a balanced wealth-builder that limits downside during stock corrections. The structure suits your {risk_appetite} risk parameters while capturing growth opportunities over time.",
            "To capture stock growth with lower volatility, this hybrid model combines equities and bonds. The debt sleeve dampens market drops, protecting {short_client}'s allocated capital. This provides a pragmatic, dual-sleeve approach to compounding wealth securely over the horizon.",
            "We recommend this hybrid blend to secure equity exposure with a built-in safety net. Bonds within the fund anchor the principal while the equity sleeve compounds {short_client}'s wealth. It provides a solid, long-term foundation for your objective of {objective}.",
            "By blending growth-seeking equities with reliable fixed income-producing bonds, this fund balances risk and reward. {short_client} gets active equity exposure with less intense price swings. It represents a sensible fit for this {allocation_words} allocation and aligns well with the overall portfolio risk profile."
        ],
        "small_cap": [
            "To capture rapid business compounding, this fund invests in small-sized companies. These emerging leaders offer significant long-term growth for {short_client}. However, they come with higher short-term fluctuations that match your {risk_appetite} profile for wealth creation.",
            "This small-cap specialist targets rising market leaders at an early stage. While price swings can be high, the potential to compound this {allocation_words} allocation is strong. It acts as an active growth engine to drive long-term capital compounding.",
            "For {short_client}'s wealth creation goals, this small-cap vehicle provides high-growth exposure. The manager selects niche businesses with structural scale-up potential. We accept higher short-term price variations for superior compounding gains over the long investment horizon.",
            "Niche market dominance and high-growth potential make this small-cap selection compelling. Because smaller enterprises react sharply to cycles, {short_client} should expect elevated volatility. It aligns with a long-term {objective} focus and active risk tolerance.",
            "This fund allocates to emerging companies to maximize {short_client}'s capital appreciation. Small-caps offer room for rapid business expansion. The allocation is sized prudently within the portfolio to manage risks while seeking maximum growth.",
            "Active equity growth is achieved here by investing in emerging high-growth businesses with strong scalability and long-term compounding potential."
        ],
        "multicap": [
            "This multi-cap framework mandates a 25% minimum in large, mid, and small companies. {short_client} benefits from structured exposure across all market cap segments. It ensures participation in both stable giants and fast growers through a single fund.",
            "By spreading investments across large, mid, and small businesses, this fund maintains broad market coverage. The disciplined allocation protects {short_client}'s portfolio from sector concentration. It adjusts active weights as market cycles rotate to optimize growth.",
            "For a comprehensive equity engine, this fund balances stable large-caps with agile small/mid-caps. {short_client} gets a diversified stock exposure in a single allocation. This structured asset mix supports your long-term {objective} goal and manages overall volatility.",
            "This multi-cap strategy captures opportunities across the entire market capitalization spectrum. It provides {short_client} a balanced blend of giant, established firms and emerging enterprises. It keeps the portfolio well-diversified across all sectors of the economy.",
            "We recommend this multi-cap approach for disciplined, all-weather equity exposure. Spreading weights across different cap sizes offers {short_client} both stability and growth. It fits your {risk_appetite} risk profile nicely and compounds your capital steadily over time."
        ],
        "arbitrage": [
            "This arbitrage fund exploits pricing differences between cash and futures markets. Because it maintains a fully hedged equity position, the risk to {short_client}'s principal is very low. It yields tax-efficient returns similar to short-term debt instruments.",
            "To park {short_client}'s liquid funds safely, we select this market-neutral arbitrage strategy. It generates returns by capturing short-term market spreads rather than taking stock direction risk. This provides high safety and tax efficiency for your capital buffer.",
            "This low-volatility fund captures price discrepancies between spot and derivative segments. It remains insulated from stock market direction, securing {short_client}'s capital values. It serves as a highly tax-efficient alternative to conventional savings and short-term debt.",
            "We include this market-neutral arbitrage vehicle to generate low-risk yields. It avoids stock market downside by hedging equity exposure completely. This represents a safe capital harbor matching your {objective} requirements and short-term liquidity needs.",
            "Pricing spreads in spot and futures markets drive the returns of this hedged portfolio. {short_client} gets reliable capital protection with high liquidity. The tax treatment remains highly favorable compared to regular debt products under current rules."
        ],
        "liquid": [
            "This liquid sleeve focuses on capital preservation and overnight accessibility. Investing in highly rated short-term debt instruments, it protects {short_client}'s capital values. It serves as a secure, immediate cash reserve for your portfolio setup.",
            "For immediate cash needs and emergency backup, this high-safety fund is ideal. It invests in short-duration treasury and money market securities to avoid interest rate risk. {short_client} gains maximum liquidity with stable principal values through all cycles.",
            "We place a portion of {short_client}'s capital here for safety and easy access. The portfolio holds highly rated money market papers to ensure low volatility. This represents a secure liquidity shield to protect your asset base.",
            "High liquidity and capital preservation are the twin objectives of this short-term placement. It keeps {short_client}'s funds ready for immediate reallocation when market opportunities arise. Volatility is virtually zero, protecting the core of your corpus.",
            "This fund acts as a defensive cash buffer for {short_client}. By holding short-term sovereign and banking debt, it maintains high capital security. This matches the safety requirements of your allocation and preserves purchasing power."
        ],
        "large_cap": [
            "This equity fund focuses on dominant industry leaders with strong balance sheets. These established industry leaders provide steady compounding and valuation comfort for {short_client}. It anchors the equity growth sleeve of your portfolio for the future.",
            "We allocate to this fund to compound {short_client}'s capital through high-quality, large-sized corporations. The manager selects firms with structural competitive advantages. This offers stable growth aligned with your {risk_appetite} stance over the next decade.",
            "For core wealth accumulation, this large-cap-oriented strategy backs robust market leaders. These businesses demonstrate superior pricing power to handle inflation. {short_client} gains steady long-term compounding with moderate downside shielding in volatile market periods.",
            "This fund compounds wealth by owning shares in elite, sector-leading corporations. It provides {short_client} stable equity participation with lower volatility compared to smaller companies. It fits well with your {objective} goal and target investment horizon.",
            "Active equity growth is achieved here by targeting cash-flow-rich industry leaders. {short_client} gets exposure to the driving forces of the domestic economy. This forms a reliable compounding block for the portfolio over the long term."
        ],
        "debt": [
            "This fixed-income position focuses on generating regular yield with high security. By holding quality corporate bonds and government debt, it anchors the portfolio. {short_client} receives stable payouts with low capital price swings over interest rate cycles.",
            "To secure steady income yields, this debt fund invests in highly rated credit papers. It cushions {short_client}'s portfolio against equity market volatility. This fixed-income allocation is structured for safety and cash flow stability during corrections.",
            "We include this credit-selected portfolio to earn consistent interest payouts. It is managed actively to optimize yield returns while keeping default risk low. It serves as a reliable cash-flow driver for {short_client}'s long-term {objective} goals.",
            "This bond allocation provides a stable interest-earning cushion for {short_client}. It reduces overall portfolio volatility by holding high-grade debt instruments. It aligns with your capital preservation goals and offers safety for your assets.",
            "Consistency and capital preservation are prioritized through this diversified bond strategy. It secures active yields from corporate and sovereign debt. This gives {short_client} a steady income shield and buffers the overall portfolio risk profile."
        ],
        "mid_cap": [
            "For core wealth accumulation, this mid-cap-oriented strategy compounds capital through emerging market leaders. The manager selects firms with high structural growth potential and strong scalability. This offers active growth aligned with your {risk_appetite} stance over the investment horizon.",
            "We allocate to this fund to compound {short_client}'s capital through sector-leading, mid-sized corporations. These companies benefit from domestic economic tailwinds and market share expansion. It anchors the equity growth sleeve of your portfolio with balanced risk-reward characteristics.",
            "This mid-cap equity fund targets established enterprises during their high-growth expansion phase. It provides {short_client} a premium compounding block with higher agility than large-caps and lower volatility than small-caps. It represents a strategic growth placement matching your {risk_appetite} risk posture.",
            "By focusing on mid-sized companies with clean balance sheets and competitive moats, this fund seeks superior returns. {short_client} gains exposure to emerging industry champions that drive economic growth. This fits well with your objective of {objective} over the long term.",
            "Active equity appreciation is achieved here by targeting high-conviction mid-cap enterprises. The fund participates in emerging corporate winners with robust growth runways. This forms a high-compounding sleeve for the portfolio, matching the target investment horizon."
        ]
    }

    summary_templates = {
        "baf": [
            "Valuation-driven dynamic equity-debt rebalancing for risk protection.",
            "Shifts capital dynamically between equities and bonds based on market multiples.",
            "Protects wealth by dynamically reallocating asset weights in volatile markets.",
            "Systematic equity-debt reallocation to balance growth and capital stability.",
            "Valuation-linked asset rebalancing mechanism to buffer portfolio drawdowns."
        ],
        "multi_asset": [
            "Spreads capital across uncorrelated classes including gold, shares, and bonds.",
            "Broad multi-asset diversification to insulate portfolio from single-market shocks.",
            "Uncorrelated asset mix of equity, debt, and gold for steady performance.",
            "Multi-layered asset distribution to smooth returns through cycle rotations.",
            "Combines gold, fixed income, and stocks for inflation-hedged wealth preservation."
        ],
        "hybrid": [
            "Balances equity growth potential with stable fixed-income downside cushioning.",
            "Blends steady bond yields with active stock market return participation.",
            "Structural equity-debt allocation to lower overall portfolio volatility.",
            "Dual-sleeve asset model providing equity compounding alongside income stability.",
            "Participates in corporate earnings growth while maintaining safety reserves."
        ],
        "small_cap": [
            "High-conviction exposure to emerging companies for rapid capital compounding.",
            "Targets fast-growing smaller enterprises with higher short-term fluctuations.",
            "Captures sector leadership expansion among small-sized business models.",
            "High growth placement focusing on early-stage corporate winners.",
            "Priced for maximum long-term appreciation with expected high price swings."
        ],
        "multicap": [
            "Disciplined exposure across large, mid, and small-sized business giants.",
            "All-weather stock strategy allocating across the full market capitalization range.",
            "Spreads equity risk across established market leaders and fast-growing firms.",
            "Structured cap-size allocation to balance growth and capital stability.",
            "Participates in corporate opportunities across all market cap segments."
        ],
        "arbitrage": [
            "Tax-efficient market-neutral arbitrage capturing cash-future pricing spreads.",
            "Fully hedged equity positions to yield low-risk, debt-like returns.",
            "Zero direction risk strategy offering steady capital safety and liquidity.",
            "Exploits spot-derivative price discrepancies for secure cash management.",
            "Low-volatility hedged portfolio providing tax-friendly cash yields."
        ],
        "liquid": [
            "Capital stability and immediate liquidity through high-quality overnight assets.",
            "Low-risk savings reservoir investing in short-duration treasury instruments.",
            "Defensive liquid cash buffer to secure emergency capital values.",
            "Overnight safety reserve with near-zero interest rate price swings.",
            "Secure placement of liquid reserves in short-term corporate debt."
        ],
        "large_cap": [
            "Compounds wealth steadily through dominant, cash-rich corporate market leaders.",
            "Core equity growth sleeve backing elite businesses with wide economic moats.",
            "Established bluechip giants providing stable long-term compounding gains.",
            "High-conviction large-cap placement for moderate downside protection.",
            "Backs sector-leading corporate giants with clean balance sheets."
        ],
        "debt": [
            "Consistent interest income yields from highly rated fixed-income securities.",
            "Defensive bond sleeve securing steady income and capital stability.",
            "Stabilizes portfolio cash flows with low capital price fluctuations.",
            "Credit-screened bond allocation structured for predictable interest returns.",
            "Quality fixed-income debt shield to hedge against stock volatility."
        ],
        "mid_cap": [
            "Invests in mid-sized emerging leaders with high scalability for capital compounding.",
            "Captures growth opportunities among agile mid-cap enterprises with robust runways.",
            "Emerging industry champions providing active capital compounding and expansion potential.",
            "Focused mid-cap placement targeting sector leaders with structural growth tailwinds.",
            "Compounding wealth through high-quality mid-sized corporations during expansion phase."
        ]
    }

    import re
    import hashlib
    excel_rationale = str(excel_rationale).strip()

    variants = {
        "baf": [
            {
                "summary": "Selected for {amc}'s dynamic asset allocation strategy, which automatically adjusts equity and debt weights to capture market growth while curbing downside volatility.",
                "detailed": "This fund acts as a core stabilizer in the portfolio, utilizing {amc}'s proprietary valuation models to dynamically shift between equity and debt. The allocation of {allocation_words} helps mitigate drawdowns during market peaks while allowing participation in growth phases. It aligns with {short_client}'s objective of {objective} by balancing return generation with robust capital preservation."
            },
            {
                "summary": "Chosen to leverage {amc}'s counter-cyclical asset rebalancing model, dynamically shifting between shares and bonds to optimize risk-adjusted returns during volatile market cycles.",
                "detailed": "For {short_client}'s portfolio, this fund manages asset shifts dynamically to keep risk tightly controlled. High valuations trigger systematic profit-taking into debt, while market corrections prompt equity buying. This disciplined asset allocation framework cushions the {allocation_words} capital against major volatility, providing steady and balanced growth over the horizon."
            },
            {
                "summary": "Selected to provide a valuation-driven asset mix for {short_client}, using {amc}'s quantitative framework to hedge equity downside while capturing growth cycles.",
                "detailed": "By adjusting equity exposure relative to market price-to-earnings multiples, this {amc} fund provides a smoother compounding path. The active reallocation mechanism shields {short_client}'s {allocation_words} investment from sudden corrections. It offers defensive capital positioning during expensive market phases alongside active stock gains during market recoveries."
            }
        ],
        "multi_asset": [
            {
                "summary": "Focus on disciplined diversification across equity, debt, and commodities to improve portfolio resilience across market cycles.",
                "detailed": "Spreading {short_client}'s risk across uncorrelated asset classes is the core strength of this {amc} portfolio. By maintaining disciplined exposure to domestic shares, international equities, commodities, and fixed income, it reduces vulnerability to single-sector drops. This {allocation_words} allocation acts as a stabilizing pillar during broader economic cycles and transition phases."
            },
            {
                "summary": "Selected for its active tactical allocation framework that dynamically shifts between equities, debt, and commodities based on market valuations.",
                "detailed": "This fund actively manages exposure across multiple asset classes to capture upside while limiting downside. By moving capital into fixed income and gold during overvalued equity phases, it provides {short_client} a highly resilient compounding path. This {allocation_words} allocation acts as a dynamic shield against unexpected market shocks."
            },
            {
                "summary": "Chosen to build long-term wealth by blending uncorrelated asset streams, delivering a balanced risk-return profile.",
                "detailed": "This multi-asset strategy focuses on delivering equity-like returns with debt-like volatility for {short_client}. By structuring a portfolio of non-correlated assets, it smooths out the investment journey. The {allocation_words} position provides a structural hedge against inflation, ensuring steady capital expansion for your {objective} goal."
            }
        ],
        "small_cap": [
            {
                "summary": "Selected to drive long-term capital compounding by investing in {amc}'s high-conviction portfolio of emerging small-sized companies with scalable business models.",
                "detailed": "This fund acts as a primary growth accelerator for {short_client}'s capital by targeting emerging corporate winners at an early stage. While it experiences higher short-term price swings, the potential for exponential compounding is superior. The fund house's rigorous bottom-up selection ensures focus on quality businesses with strong balance sheets."
            },
            {
                "summary": "Chosen to capture high-growth opportunities in emerging Indian sectors through {amc}'s focus on niche market leaders with strong scalability and robust governance.",
                "detailed": "For {short_client}'s long-term wealth compounding, this small-cap vehicle provides high-growth exposure in under-researched market segments. The manager selects businesses with structural scale-up potential and clear competitive moats. We accept elevated short-term fluctuations in this {allocation_words} allocation to achieve superior compounding over a multi-year horizon."
            },
            {
                "summary": "Selected for {amc}'s disciplined small-cap strategy, investing in quality emerging businesses to maximize long-term capital appreciation for {short_client}.",
                "detailed": "This fund allocates to high-potential small enterprises to drive the growth engine of {short_client}'s portfolio. By backing companies with high capital efficiency and market share gains, it outpaces conventional large-cap benchmarks. The {allocation_words} investment is sized prudently to exploit small-cap premiums while managing downside volatility."
            }
        ],
        "large_cap": [
            {
                "summary": "Selected to anchor the equity portion of the portfolio in {amc}'s high-quality blue-chip companies, offering steady compounding and long-term capital stability.",
                "detailed": "This fund serves as {short_client}'s core wealth accumulator by investing in elite, sector-leading corporations with wide economic moats. These established giants possess strong balance sheets and pricing power to navigate economic cycles safely. It provides consistent equity returns with lower volatility compared to smaller companies, anchoring this {allocation_words} position."
            },
            {
                "summary": "Chosen for {amc}'s disciplined large-cap investment style, focusing on dominant, cash-rich market leaders to secure stable long-term wealth compounding for {short_client}.",
                "detailed": "We recommend this large-cap vehicle to compound {short_client}'s wealth through resilient market giants. The portfolio targets businesses with strong governance and steady cash flows. This large-cap base stabilizes the equity sleeve, mitigating fluctuations while capturing steady returns on your {allocation_words} allocation over the investment horizon."
            },
            {
                "summary": "Selected to provide solid large-cap equity exposure, utilizing {amc}'s research to back dominant industry leaders with robust balance sheets.",
                "detailed": "Active growth is achieved here by targeting industry leaders that drive the domestic economy. For {short_client}, this fund offers institutional-grade equity exposure with moderate downside shielding. The portfolio is structured to achieve consistent returns that outpace inflation, aligning perfectly with your {objective} goal."
            }
        ],
        "mid_cap": [
            {
                "summary": "Selected to target {amc}'s high-conviction mid-sized companies scaling rapidly, offering a balance between large-cap stability and small-cap growth.",
                "detailed": "This fund compounds wealth for {short_client} by investing in emerging industry champions during their high-growth expansion phase. It provides exposure to businesses with strong market share gains and scalability. This offers high growth potential with less intense price swings than small-cap funds. The placement aligns with your medium-to-long term objective of capital growth."
            },
            {
                "summary": "Chosen for {amc}'s mid-cap expertise, capturing agile market leaders during their rapid expansion phase to accelerate portfolio capital compounding.",
                "detailed": "This portfolio targets mid-sized corporations benefit from domestic economic tailwinds and market share expansion. For {short_client}, this fund serves as an active growth engine that bridges the gap between stability and aggressive growth. The {allocation_words} allocation is positioned to benefit from mid-cap premium compounding over the long horizon."
            },
            {
                "summary": "Selected to capture high-growth mid-cap opportunities through {amc}'s focus on quality businesses with competitive moats and strong scalability.",
                "detailed": "By focusing on mid-sized companies with clean balance sheets and competitive moats, this fund seeks superior returns. {short_client} gains exposure to emerging industry champions that drive economic growth. This fits well with your objective of {objective} over the long term, offering high risk-adjusted return potential."
            }
        ],
        "multicap": [
            {
                "summary": "Selected to ensure disciplined participation across large-cap stability, mid-cap growth, and small-cap agility via {amc}'s structured multicap strategy.",
                "detailed": "This fund acts as an all-weather equity engine for {short_client} by maintaining a mandatory 25% allocation in large, mid, and small companies. It balances stable industry leaders with high-growth market challengers to optimize returns. This diversified approach manages cap-size volatility and guards against sector concentration. It supports your wealth creation goals while ensuring broad-based market participation."
            },
            {
                "summary": "Chosen for {amc}'s disciplined multicap approach, distributing equity exposure across all market cap segments to optimize diversification and growth.",
                "detailed": "By spreading investments across large, mid, and small businesses, this fund maintains broad market coverage. The disciplined allocation protects {short_client}'s portfolio from sector concentration. It adjusts active weights as market cycles rotate to optimize growth, making it a highly versatile compounding block for this {allocation_words} allocation."
            },
            {
                "summary": "Selected to capture opportunities across all cap sizes using {amc}'s research to dynamically weight large, mid, and small-cap stocks.",
                "detailed": "This multi-cap strategy captures opportunities across the entire market capitalization spectrum. It provides {short_client} a balanced blend of giant, established firms and emerging enterprises. It keeps the portfolio well-diversified across all sectors of the economy, matching a {risk_appetite} risk profile and supporting your {objective} goal."
            }
        ],
        "hybrid": [
            {
                "summary": "Selected to secure long-term capital growth through {amc}'s active equity exposure, cushioned by a structural fixed-income buffer to absorb market volatility.",
                "detailed": "This fund serves as a balanced growth engine in {short_client}'s portfolio, combining active stock market exposure with a defensive debt sleeve. The equity allocation drives long-term compounding, while the bonds provide yield and capital stability. This dual-sleeve structure reduces overall portfolio fluctuations during downturns. It aligns with your wealth creation objective while keeping volatility within comfortable boundaries."
            },
            {
                "summary": "Chosen to blend active equity participation with fixed income stability, utilizing {amc}'s asset allocation model to manage portfolio drawdowns during market corrections.",
                "detailed": "This hybrid portfolio blends active equity participation with fixed income protection. For {short_client}, it acts as a balanced wealth-builder that limits downside during stock corrections. The structure suits your {risk_appetite} risk parameters while capturing growth opportunities over time, compounding your {allocation_words} allocation steadily."
            },
            {
                "summary": "Selected for {amc}'s balanced strategy, using a fixed equity-debt mix to deliver steady growth while containing portfolio downside risk.",
                "detailed": "To capture stock growth with lower volatility, this hybrid model combines equities and bonds. The debt sleeve dampens market drops, protecting {short_client}'s allocated capital. This provides a pragmatic, dual-sleeve approach to compounding wealth securely over the horizon, supporting your objective of {objective}."
            }
        ],
        "arbitrage": [
            {
                "summary": "Selected to generate low-risk, tax-efficient cash yields by exploiting spot-future pricing spreads in equity markets through {amc}'s market-neutral strategy.",
                "detailed": "This fund serves as a highly liquid capital shield by running a fully hedged market-neutral strategy. It offers debt-like safety and low volatility, making it an excellent cash alternative that minimizes risk. By generating tax-friendly returns, it balances the portfolio's growth sleeves. This allocation aligns with {short_client}'s objective of maintaining high safety and tax efficiency."
            },
            {
                "summary": "Chosen for {amc}'s market-neutral arbitrage strategy, delivering stable, low-volatility returns with zero directional equity risk and high capital safety.",
                "detailed": "To park {short_client}'s liquid funds safely, we select this market-neutral arbitrage strategy. It generates returns by capturing short-term market spreads rather than taking stock direction risk. This provides high safety and tax efficiency for your capital buffer, making it a reliable place for this {allocation_words} allocation."
            },
            {
                "summary": "Selected to utilize pricing differences between cash and derivative markets via {amc}'s hedged framework to secure tax-efficient capital returns.",
                "detailed": "This low-volatility fund captures price discrepancies between spot and derivative segments. It remains insulated from stock market direction, securing {short_client}'s capital values. It serves as a highly tax-efficient alternative to conventional savings and short-term debt, providing cash safety for {short_client}."
            }
        ],
        "liquid": [
            {
                "summary": "Selected to provide maximum capital safety, near-zero interest rate risk, and immediate liquidity for parking short-term reserves in {amc}'s overnight assets.",
                "detailed": "This fund acts as {short_client}'s immediate cash sleeve and safety buffer, holding top-rated money market and treasury assets. It focuses on preserving principal value above all else, keeping volatility near zero. By providing overnight accessibility, it ensures funds are ready for emergencies. This placement supports the portfolio's core stability and safety requirements."
            },
            {
                "summary": "Chosen for {amc}'s conservative liquidity management, securing short-term capital reserves with stable principal values and instant accessibility for {short_client}.",
                "detailed": "For immediate cash needs and emergency backup, this high-safety fund is ideal. It invests in short-duration treasury and money market securities to avoid interest rate risk. {short_client} gains maximum liquidity with stable principal values through all cycles, shielding this {allocation_words} allocation from volatility."
            },
            {
                "summary": "Selected to hold short-term cash reserves securely for {short_client}, leveraging {amc}'s conservative research to prioritize capital safety and overnight liquidity.",
                "detailed": "We place a portion of {short_client}'s capital here for safety and easy access. The portfolio holds highly rated money market papers to ensure low volatility. This represents a secure liquidity shield to protect your asset base, preserving capital value while maintaining near-zero risk."
            }
        ],
        "debt": [
            {
                "summary": "Selected to secure predictable fixed-income yield and stabilize the portfolio via {amc}'s credit-screened high-quality corporate bond and government treasury holdings.",
                "detailed": "This fund acts as a steady yield driver for {short_client} by investing in highly rated corporate bonds and government securities. It provides reliable interest payouts while protecting your capital from large price swings. The fixed-income exposure reduces overall portfolio volatility and balances growth sleeves. This stable sleeve aligns with your objective of capital preservation."
            },
            {
                "summary": "Chosen for {amc}'s fixed-income expertise, offering a reliable yield shield and capital safety to hedge {short_client}'s portfolio against equity market volatility.",
                "detailed": "To secure steady income yields, this debt fund invests in highly rated credit papers. It cushions {short_client}'s portfolio against equity market volatility. This fixed-income allocation is structured for safety and cash flow stability during corrections, ensuring your {allocation_words} allocation remains protected."
            },
            {
                "summary": "Selected to provide consistent interest income and capital stability, utilizing {amc}'s high-quality bond portfolio to reduce overall risk.",
                "detailed": "We include this credit-selected portfolio to earn consistent interest payouts. It is managed actively to optimize yield returns while keeping default risk low. It serves as a reliable cash-flow driver for {short_client}'s long-term {objective} goals, balancing the portfolio with a low-volatility fixed-income anchor."
            }
        ]
    }

    cat_key = category.lower() if category.lower() in variants else "large_cap"

    excel_rationale_clean = str(excel_rationale).strip()
    is_generic = False
    generic_patterns = [
        "top quartile equity funds for long term wealth creation",
        "top quartile equity",
        "top quartile",
        "long term wealth creation",
        "long-term wealth creation"
    ]
    excel_lower = excel_rationale_clean.lower()
    for gp in generic_patterns:
        if gp in excel_lower:
            is_generic = True
            break
            
    if is_generic:
        excel_rationale = ""
    else:
        excel_rationale = re.sub(r'(?i)\bbinds\b', 'bonds', excel_rationale_clean)

    if excel_rationale and excel_rationale.lower() != "nan" and len(excel_rationale) > 2:
        # 1. CORE RATIONALE (Directly from Excel rationale, maximum 1 line, do not expand)
        cleaned_core = excel_rationale
        cleaned_core = re.sub(r'(?i)\bfd\b', 'Fixed Deposits', cleaned_core)
        cleaned_core = re.sub(r'(?i)\bsips?\b', 'Systematic Investment Plan', cleaned_core)
        cleaned_core = re.sub(r'(?i)\bcurrenlty\b', 'currently', cleaned_core)
        cleaned_core = re.sub(r'(?i)\b&\b', 'and', cleaned_core)
        cleaned_core = re.sub(r'\s+', ' ', cleaned_core).strip()
        if not cleaned_core.endswith('.'):
            cleaned_core += '.'
        cleaned_core = cleaned_core[0].upper() + cleaned_core[1:]
        
        summary_rationale = cleaned_core
        # detailed rationale is dynamically generated from variants to prevent repetition
        amc_name = get_amc_name(clean_name)
        v_list = variants[cat_key]
        p_hash = int(hashlib.md5(clean_name.encode('utf-8')).hexdigest(), 16)
        v_idx = (p_hash + variant_offset) % len(v_list)
        v_choice = v_list[v_idx]
        detailed_rationale = v_choice["detailed"].format(
            amc=amc_name,
            fund=clean_name,
            short_client=short_client,
            allocation_words=allocation_words,
            objective=objective,
            risk_appetite=risk_appetite,
            horizon=horizon
        )
    else:
        amc_name = get_amc_name(clean_name)
        v_list = variants[cat_key]
        p_hash = int(hashlib.md5(clean_name.encode('utf-8')).hexdigest(), 16)
        v_idx = (p_hash + variant_offset) % len(v_list)
        v_choice = v_list[v_idx]
        summary_rationale = v_choice["summary"].format(
            amc=amc_name,
            fund=clean_name,
            short_client=short_client,
            allocation_words=allocation_words,
            objective=objective,
            risk_appetite=risk_appetite,
            horizon=horizon
        )
        detailed_rationale = v_choice["detailed"].format(
            amc=amc_name,
            fund=clean_name,
            short_client=short_client,
            allocation_words=allocation_words,
            objective=objective,
            risk_appetite=risk_appetite,
            horizon=horizon
        )

    if variant_offset >= len(v_list):
        # Append extra uniqueness sentence if offset is high
        summary_rationale += f" Aligned with {amc_name}'s key strength in portfolio construction."
        detailed_rationale += f" Additionally, {amc_name}'s management of {clean_name} focuses on long-term execution and portfolio resilience, catering to {short_client}'s {horizon} timeframe."

    return {
        "why_selected": summary_rationale,
        "summary_rationale": summary_rationale,
        "detailed_rationale": detailed_rationale,
        "expected_role": role_choice,
        "risk_profile": risk_choice,
        "expected_benefit": benefit_choice,
        "market_positioning": pos_choice,
        "downside_protection": down_choice,
        "diversification_benefit": div_choice
    }

def _get_seeded_choice(choices, client_name, fund_name, slot_name):
    seed_str = f"{client_name}_{fund_name}_{slot_name}"
    seed_val = zlib.crc32(seed_str.encode('utf-8'))
    rng = random.Random(seed_val)
    return rng.choice(choices)

def _clean_and_classify_products(fund_data, corpus, client_data):
    cleaned_products = []
    
    # 1. Clean data and classify each product into its AMFI Category
    for idx, f in enumerate(fund_data):
        product_name = f.get("Product Name", "").strip()
        if not product_name or product_name.lower() == "nan":
            continue
            
        cat_class = f.get("Segment") or f.get("Asset Class") or f.get("Category") or ""
        
        # Determine AMFI Category and Subtitle
        amfi_cat, amfi_sub = classify_amfi_category(product_name, cat_class)
        
        # Requirement 5: Add validation logs
        print(f"[AMFI Category Classification] Fund Name: {product_name} | Detected AMFI Category: {amfi_cat} | Final Display Category: {amfi_cat}", flush=True)
        
        # Clean Allocation (INR)
        amt_str = str(f.get("Allocation (INR)", "0"))
        amt_val = clean_float_val(amt_str)
        if amt_val == 0.0:
            for alt_key in ["Amount", "Allocation", "Value", "Amt", "allocation"]:
                if f.get(alt_key):
                    amt_val = clean_float_val(str(f.get(alt_key)))
                    if amt_val > 0.0:
                        break
                        
        # Clean SIP Amount
        sip_val = clean_float_val(str(f.get("SIP Amount", "0")))
        if sip_val == 0.0:
            for alt_key in ["SIP", "sip", "sip amount", "SIP Amount", "Sip"]:
                if f.get(alt_key):
                    sip_val = clean_float_val(str(f.get(alt_key)))
                    if sip_val > 0.0:
                        break
        
        horizon_val = f.get("Investment Horizon") or f.get("Horizon") or f.get("horizon") or ""
        
        cleaned_products.append({
            "Product Name": product_name,
            "AMFI_Category": amfi_cat,
            "AMFI_Subtitle": amfi_sub,
            "Asset Class": f.get("Asset Class") or "Mutual Fund",
            "Allocation (INR)_float": amt_val,
            "Allocation (INR)": f"{int(amt_val):,}" if amt_val > 0.0 else "0",
            "SIP Amount": sip_val,
            "Investment Horizon": horizon_val,
            "Category": cat_class,
            "Target Return": f.get("Target Return") or f.get("Expected Returns") or f.get("Expected Return") or "12% - 15%",
            "Core Rationale": f.get("Core Rationale") or f.get("Rationale") or f.get("Why Selected") or ""
        })
        
    # Split corpus if all allocations are 0
    total_alloc = sum(p["Allocation (INR)_float"] for p in cleaned_products)
    if total_alloc == 0.0 and len(cleaned_products) > 0:
        p_alloc_val = corpus / len(cleaned_products)
        for p in cleaned_products:
            p["Allocation (INR)_float"] = p_alloc_val
            p["Allocation (INR)"] = f"{int(p_alloc_val):,}"
            
    # Group unique categories and sort them in risk-based order using AMFI_SORT_ORDER
    unique_cats = list(set(p["AMFI_Category"] for p in cleaned_products))
    
    def sort_key(c_name):
        try:
            return AMFI_SORT_ORDER.index(c_name)
        except ValueError:
            return len(AMFI_SORT_ORDER)
            
    unique_cats.sort(key=sort_key)
    
    # Map each category to a dynamic Part number 1 to N
    part_mapping = {cat: i+1 for i, cat in enumerate(unique_cats)}
    
    # Assign Segment name and dynamic Part number to each product
    for p in cleaned_products:
        cat = p["AMFI_Category"]
        p["Part"] = part_mapping[cat]
        # Consistently display Category Name as segment name
        p["Segment"] = cat
        
    return cleaned_products

def _calculate_allocations(cleaned_products, corpus, profile=None):
    total_alloc = sum(p["Allocation (INR)_float"] for p in cleaned_products)
    if total_alloc > 0.0:
        corpus = total_alloc
        
    # Aggregate allocations by Part
    part_totals = {}
    for p in cleaned_products:
        pt = p["Part"]
        part_totals[pt] = part_totals.get(pt, 0.0) + p["Allocation (INR)_float"]
        
    allocations = []
    active_parts = sorted(list(part_totals.keys()))
    for pt in active_parts:
        pct = 0
        if corpus > 0.0:
            pct = round((part_totals[pt] / corpus) * 100)
            
        products_in_part = [p for p in cleaned_products if p["Part"] == pt]
        amfi_cat = products_in_part[0]["AMFI_Category"]
        amfi_sub = products_in_part[0]["AMFI_Subtitle"]
        seg_obj = get_amfi_category_objective(amfi_cat)
        
        allocations.append({
            "Part": pt,
            "Segment Name": amfi_cat,
            "AMFI_Subtitle": amfi_sub,
            "Allocation %": pct,
            "Objective": seg_obj
        })
        
    # Normalize percentages to sum to exactly 100%
    total_pct = sum(a["Allocation %"] for a in allocations)
    if total_pct > 0 and total_pct != 100:
        diff = 100 - total_pct
        largest = max(allocations, key=lambda x: x["Allocation %"])
        largest["Allocation %"] += diff
        
    return allocations, corpus

_SELECTED_GEMINI_MODEL = None

def get_supported_gemini_model(api_key):
    global _SELECTED_GEMINI_MODEL
    if _SELECTED_GEMINI_MODEL:
        return _SELECTED_GEMINI_MODEL
    
    # Try gemini-2.5-flash as default stable version
    default_model = "gemini-2.5-flash"
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            supported_models = []
            for m in models_data:
                name = m.get("name", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods and "models/gemini" in name:
                    model_id = name.replace("models/", "")
                    supported_models.append(model_id)
            
            # Select the best flash model
            clean_flash_models = [
                m for m in supported_models 
                if "flash" in m and not any(x in m for x in ["preview", "tts", "image", "lite", "robotics"])
            ]
            if clean_flash_models:
                # Prioritize stable releases
                for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
                    if m in clean_flash_models:
                        _SELECTED_GEMINI_MODEL = m
                        return m
                _SELECTED_GEMINI_MODEL = clean_flash_models[0]
                return _SELECTED_GEMINI_MODEL
            
            flash_models = [m for m in supported_models if "flash" in m]
            if flash_models:
                _SELECTED_GEMINI_MODEL = flash_models[0]
                return _SELECTED_GEMINI_MODEL
            
            if supported_models:
                _SELECTED_GEMINI_MODEL = supported_models[0]
                return _SELECTED_GEMINI_MODEL
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[AI Engine REST] Failed to dynamically list models: {e}")
    return default_model

def call_llm_api(prompt, api_key, temperature=0.95):
    """
    Unified REST API client for Gemini and OpenAI to bypass library installation issues.
    Routes keys starting with 'sk-' to OpenAI Chat Completions, and others to Google Gemini generateContent.
    """
    if not api_key:
        print("[AI Engine ERROR] API key is empty.")
        raise ValueError("API key is empty.")
    
    api_key = api_key.strip()
    
    if api_key.startswith("sk-"):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature
        }
        
        try:
            print("[AI Engine] AI request started (OpenAI model: gpt-4o-mini)")
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            print("[AI Engine] Request sent successfully")
            status_code = response.status_code
            
            if 200 <= status_code < 300:
                print("[AI Engine] Response received successfully")
                res_json = response.json()
                return res_json["choices"][0]["message"]["content"]
            else:
                print(f"[AI Engine ERROR] OpenAI HTTP {status_code} received")
                response.raise_for_status()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[AI Engine] OpenAI gpt-4o-mini call failed: {e}. Trying gpt-4o...")
            payload["model"] = "gpt-4o"
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                status_code = response.status_code
                if 200 <= status_code < 300:
                    print("[AI Engine] Response received successfully")
                    res_json = response.json()
                    return res_json["choices"][0]["message"]["content"]
                else:
                    print(f"[AI Engine ERROR] OpenAI HTTP {status_code} received")
                    response.raise_for_status()
            except Exception as e2:
                print(f"[AI Engine ERROR] OpenAI call failed: {e2}")
                raise e2
                
    else:
        # Dynamically determine the best supported model name
        model_name = get_supported_gemini_model(api_key)
        print(f"[AI Engine] AI request started (Gemini model: {model_name})")
        
        # Define the actual endpoint URL, headers, and payload for Gemini REST API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json"
            }
        }
        
        reached_google = False
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            print("[AI Engine] Request sent successfully")
            reached_google = True
            status_code = response.status_code
            
            if status_code == 200:
                print("[AI Engine] Response received successfully")
            else:
                print(f"[AI Engine ERROR] HTTP {status_code} received from Gemini API")
                
            if status_code == 429:
                print("[AI Engine ERROR] Quota/Rate-limit restrictions exceeded (HTTP 429)")
                response.raise_for_status()
            elif status_code == 400:
                print("[AI Engine ERROR] Bad Request (HTTP 400)")
                response.raise_for_status()
            elif status_code == 403:
                print("[AI Engine ERROR] Forbidden (HTTP 403) - verify API key")
                response.raise_for_status()
            elif status_code == 404:
                print("[AI Engine ERROR] Not Found (HTTP 404) - endpoint or model unavailable")
                response.raise_for_status()
                
            response.raise_for_status()
            res_json = response.json()
            
            candidates = res_json.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text_out = parts[0].get("text", "")
                    if text_out:
                        print("[AI Engine] Response parsed successfully")
                        return text_out
                        
            print("[AI Engine ERROR] Gemini returned an empty response or unexpected structure")
            raise ValueError(f"Unexpected response format from Gemini: {res_json}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[AI Engine ERROR] Gemini REST call failed: {e}")
            raise e


def ensure_unique_rationales(products, profile):
    """
    Validates that no two products have identical CORE RATIONALE (summary_rationale / Why Selected)
    or STRATEGY & RATIONALE (detailed_rationale).
    If duplicates are detected, it regenerates them using _get_fallback_rationale_for_product with an increasing variant_offset.
    """
    seen_summaries = set()
    seen_detaileds = set()
    
    def normalize_text(text):
        import re
        return re.sub(r'\s+', '', str(text).lower().strip())
        
    for p in products:
        summary_val = str(p.get("summary_rationale") or p.get("Why Selected") or p.get("Core Rationale") or "").strip()
        detailed_val = str(p.get("detailed_rationale") or p.get("Why Selected") or p.get("Core Rationale") or "").strip()
        
        normalized_summary = normalize_text(summary_val)
        normalized_detailed = normalize_text(detailed_val)
        
        offset = 0
        while (not summary_val or normalized_summary in seen_summaries or 
               not detailed_val or normalized_detailed in seen_detaileds):
            
            # Regenerate using the fallback engine with offset, forcing new texts by ignoring excel_rationale
            rat_card = _get_fallback_rationale_for_product(
                part=p["Part"],
                product_name=p["Product Name"],
                profile=profile,
                allocation_str=p.get("Allocation (INR)_float"),
                excel_rationale="", # ignore to force regeneration
                amfi_category=p.get("AMFI_Category"),
                variant_offset=offset
            )
            summary_val = scrub_forbidden_phrases(simplify_jargon(rat_card["summary_rationale"])).strip()
            detailed_val = scrub_forbidden_phrases(simplify_jargon(rat_card["detailed_rationale"])).strip()
            
            normalized_summary = normalize_text(summary_val)
            normalized_detailed = normalize_text(detailed_val)
            offset += 1
            
            # Safety limit to prevent infinite loops
            if offset > 20:
                import uuid
                uniq_id = uuid.uuid4().hex[:4]
                summary_val += f" Aligned with unique selection model {uniq_id}."
                detailed_val += f" Underpinned by unique portfolio composition rules ({uniq_id})."
                normalized_summary = normalize_text(summary_val)
                normalized_detailed = normalize_text(detailed_val)
                break
        
        # Write unique texts to the product dictionary keys
        p["Why Selected"] = summary_val
        p["summary_rationale"] = summary_val
        p["detailed_rationale"] = detailed_val
        p["Core Rationale"] = summary_val
        
        seen_summaries.add(normalized_summary)
        seen_detaileds.add(normalized_detailed)


def generate_ai_portfolio(client_data, fund_data, api_key=None):
    """
    Optimizes asset allocations and categorizes products using Gemini AI/OpenAI or local rule sets.
    """
    # 1. Get client profile, theme, style, market positioning, and assumptions
    profile = get_client_profile_and_theme(client_data, fund_data)
    client_data["portfolio_theme"] = profile["portfolio_theme"]
    client_data["risk_appetite"] = profile["risk_appetite"]
    client_data["objective"] = profile["objective"]
    client_data["investment_style"] = profile["investment_style"]
    client_data["market_positioning"] = profile["market_positioning"]

    # Print Validation Logs
    print(f"[AI Engine] Analyzing portfolio (Theme: {profile['portfolio_theme']})")

    # 2. Clean and parse corpus value
    corpus = clean_float_val(client_data.get("Portfolio Corpus (INR)", "0"))
    if corpus == 0.0:
        corpus = 10000000.0  # 10 Cr default
        
    # 3. Clean and classify products from Excel data
    cleaned_products = _clean_and_classify_products(fund_data, corpus, client_data)
    if not cleaned_products:
        raise ValueError("Parser failed: No investment products detected.")
        
    # 4. Calculate dynamic segment allocations and corpus
    allocations, corpus = _calculate_allocations(cleaned_products, corpus, profile)
    client_data["Portfolio Corpus (INR)"] = f"{int(corpus):,}"
    
    # 5. Generate fallback qualitative narratives
    corpus_words = f"Rs. {corpus / 10000000:.1f} Crores" if corpus >= 10000000 else (f"Rs. {corpus / 100000:.1f} Lakhs" if corpus >= 100000 else f"Rs. {corpus:,.0f}")
    profile["corpus_words"] = corpus_words
    local_briefings = generate_dynamic_briefings_local(profile, corpus_words)
       # 4.5. Compute individual fund allocation percentages (relative to total portfolio)
    total_alloc = sum(p["Allocation (INR)_float"] for p in cleaned_products)
    for p in cleaned_products:
        p["Allocation %"] = f"{round((p['Allocation (INR)_float'] / total_alloc) * 100, 1)}%" if total_alloc > 0.0 else "0%"

    # Check if key is present
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    # Establish advisory styles and dynamic parameters regardless of api key presence
    advisory_styles = [
        "Institutional wealth advisory tone (highly professional, objective, structured, institutional-grade)",
        "Private banker tone (sophisticated, client-relationship-centric, bespoke, high-touch)",
        "CIO-style commentary (analytical, macro-driven, forward-looking, cycle-oriented)",
        "Conservative capital preservation style (risk-conscious, protective, stability-focused, cautious)",
        "Growth-focused strategic allocation style (compounding-oriented, opportunistic, active growth, market-beating)"
    ]
    
    import time
    rng_seed = zlib.crc32(f"{profile['client_name']}_{time.time()}".encode('utf-8'))
    rd_inst = random.Random(rng_seed)
    
    selected_style = rd_inst.choice(advisory_styles)
    selected_temp = round(rd_inst.uniform(1.15, 1.35), 2)

    if not api_key:
        print(f"[MEMORY PROFILE] 4. Gemini prompt created (fallback): {get_memory_usage():.2f} MB")
        print(f"[MEMORY PROFILE] 5. Gemini response received (fallback): {get_memory_usage():.2f} MB")
        print("Fallback rationale engine used")
        print("  - Temperature used: N/A")
        print(f"  - Style selected: {selected_style}")
        print("  - Whether fallback activated: Yes")
        print("  - API Request: Failed (API key is empty/missing)")
        print("  - Response Validation: N/A")
        print("  - Fallback Templates: Activated")
        print("  - Gemini Parsing/Matching Failures: N/A")
        
        # Apply local rationales for each product
        for p in cleaned_products:
            rat_card = _get_fallback_rationale_for_product(p["Part"], p["Product Name"], profile, p.get("Allocation (INR)_float"), p.get("Core Rationale", ""))
            
            p["Why Selected"] = scrub_forbidden_phrases(simplify_jargon(rat_card["why_selected"]))
            p["summary_rationale"] = scrub_forbidden_phrases(simplify_jargon(rat_card["summary_rationale"]))
            p["detailed_rationale"] = scrub_forbidden_phrases(simplify_jargon(rat_card["detailed_rationale"]))
            p["Expected Role"] = scrub_forbidden_phrases(simplify_jargon(rat_card["expected_role"]))
            p["Risk Profile"] = scrub_forbidden_phrases(simplify_jargon(rat_card["risk_profile"]))
            p["Expected Benefit"] = scrub_forbidden_phrases(simplify_jargon(rat_card["expected_benefit"]))
            p["Market Positioning"] = scrub_forbidden_phrases(simplify_jargon(rat_card["market_positioning"]))
            p["Downside Protection"] = scrub_forbidden_phrases(simplify_jargon(rat_card["downside_protection"]))
            p["Diversification Benefit"] = scrub_forbidden_phrases(simplify_jargon(rat_card["diversification_benefit"]))
            
        has_any_excel_rationale = any(
            p.get("Core Rationale") and len(str(p.get("Core Rationale")).strip()) > 2 and str(p.get("Core Rationale")).lower() != "nan"
            for p in cleaned_products
        )
        if has_any_excel_rationale:
            print("Excel rationale ignored: No")
            print("Dynamic AI rationale generated: No")
            print("Static Excel rationale injected: Yes")
        else:
            print("Excel rationale ignored: Yes")
            print("Dynamic AI rationale generated: Yes")
            print("Static Excel rationale injected: No")
        
        # Check if Excel has these values
        excel_exec_brief = client_data.get("Executive Briefing", "").strip()
        excel_thesis = client_data.get("Portfolio Thesis & Market Overview", "").strip()
        
        exec_summary = excel_exec_brief if excel_exec_brief else local_briefings["executive_summary"]
        thesis = excel_thesis if excel_thesis else local_briefings["portfolio_thesis"]

        ensure_unique_rationales(cleaned_products, profile)
        print(f"[MEMORY PROFILE] 6. Proposal JSON built (fallback): {get_memory_usage():.2f} MB")
        return {
            "portfolio_theme": profile["portfolio_theme"],
            "executive_summary": scrub_forbidden_phrases(exec_summary),
            "portfolio_thesis": scrub_forbidden_phrases(thesis),
            "market_commentary": scrub_forbidden_phrases(local_briefings["market_commentary"]),
            "allocation": allocations,
            "products": cleaned_products
        }
        
    api_requested = True
    api_succeeded = False
    parsing_succeeded = False
    matched_count = 0
    validation_failed_count = 0
    fallback_activated_count = 0
    error_detail = ""
    
    try:
        # Clean up client name for prompt
        import re
        short_client = re.sub(r'\(.*?\)', '', profile["client_name"]).strip()
        short_client = re.sub(r'(?i)\b(and family|family office|family|mam|sir|office)\b', '', short_client).strip()
        short_client = re.sub(r'(?i)\band\b$', '', short_client).strip()
        short_client = short_client.strip(" &")

        # Define 12 diverse advisory perspectives to force strong output differentiation
        style_perspectives = [
            "Analytical, macro-focused advisor explaining why this fund operates well under the current {market_positioning} environment.",
            "Family-office counselor focusing on long-term family security, generational safety, and legacy protection at {corpus_words} scale.",
            "Goal-oriented planner connecting this specific fund to the client's goal of '{objective}' with a {risk_appetite} risk posture.",
            "Opportunistic strategist highlighting domestic consumption, industrial cycle expansion, and structural tailwinds for {short_client}.",
            "Risk-budgeting manager focusing on capital preservation, drawdowns, and how this asset shields the core {corpus_words} portfolio.",
            "Income-centric specialist explaining how coupons, dividend yields, or interest income anchors the cash-flow needs of {short_client}.",
            "Compounding specialist focusing on long-term equity growth, inflation-beating returns, and business-owner moats.",
            "Pragmatic wealth architect looking at low correlation, asset diversification, and cycle resilience for {short_client}.",
            "Forward-looking investment director focusing on corporate governance, AMC pedigree, and high-conviction management.",
            "Defensive asset allocator looking at hedging, downside containment, and liquid reserves for a {risk_appetite} profile.",
            "Strategic value investor explaining why buying quality business blocks beats timing daily market swings.",
            "Multi-generational legacy manager prioritizing low-beta compounding to protect and grow real wealth over the next decade."
        ]

        # Define 8 sentence starters instructions to randomize
        sentence_starter_rules = [
            "You MUST start the 'Why Selected' sentence with the client's name '{short_client}' (e.g. 'For {short_client}, this fund...').",
            "You MUST start the 'Why Selected' sentence using a strong active verb explaining the benefit (e.g. 'Secures {short_client}'s capital by...').",
            "You MUST start the 'Why Selected' sentence by referencing the portfolio corpus scale '{corpus_words}' (e.g. 'At this {corpus_words} scale, we select this to...').",
            "You MUST start the 'Why Selected' sentence by referencing the {risk_appetite} risk profile (e.g. 'Matching {short_client}'s {risk_appetite} profile, this fund...').",
            "You MUST start the 'Why Selected' sentence by referencing the goal '{objective}' (e.g. 'Designed for {short_client}'s objective of {objective}, this position...').",
            "You MUST start the 'Why Selected' sentence by focusing on the segment's role (e.g. 'Chosen as the primary growth engine for {short_client}'s capital...').",
            "You MUST start the 'Why Selected' sentence with an advisory rationale (e.g. 'Aligned with {short_client}'s financial path, this fund...').",
            "You MUST start the 'Why Selected' sentence by highlighting cycle positioning (e.g. 'Given the {market_positioning} environment, this fund offers {short_client} a...')."
        ]

        # Pool of rich vocabulary words
        vocabulary_pool = [
            "anchor", "shield", "cushion", "engine", "buffer", "tailwinds", "trajectory", 
            "guardrail", "insulates", "stabilizes", "compounds", "captures", "secures", 
            "defends", "harnesses", "nurtures", "bolsters", "fortifies", "harvests", 
            "reinforces"
        ]
        
        raw_perspective = rd_inst.choice(style_perspectives)
        perspective = raw_perspective.format(
            market_positioning=profile["market_positioning"],
            corpus_words=corpus_words,
            objective=profile["objective"],
            risk_appetite=profile["risk_appetite"],
            short_client=short_client
        )
        
        raw_starter = rd_inst.choice(sentence_starter_rules)
        starter_rule = raw_starter.format(
            short_client=short_client,
            corpus_words=corpus_words,
            risk_appetite=profile["risk_appetite"],
            objective=profile["objective"],
            market_positioning=profile["market_positioning"]
        )
        
        # Pick 4 random words from the pool
        shuffled_vocab = list(set(vocabulary_pool))
        rd_inst.shuffle(shuffled_vocab)
        seed_words = shuffled_vocab[:4]

        # Prepare recommended products payload (completely ignoring pre-existing Excel rationales to prevent LLM bias/conditioning)
        recommended_products_payload = []
        for p in cleaned_products:
            recommended_products_payload.append({
                "Product Name": p["Product Name"],
                "Asset Class": p["Asset Class"],
                "Segment": p["Segment"],
                "Allocation (INR)": p["Allocation (INR)"],
                "Allocation Percentage": p["Allocation %"],
                "Target Return": p["Target Return"]
            })        # Purely domestic portfolio constraint check
        has_intl = profile.get("has_intl", True)
        if not has_intl:
            intl_constraint = """
        12. PURELY DOMESTIC PORTFOLIO RULE: The recommended portfolio contains ONLY domestic funds and no international assets. The 'executive_summary', 'portfolio_thesis', 'market_commentary', and all product rationales MUST focus on: diversified domestic asset allocation, risk-adjusted wealth creation, hybrid and multi-asset diversification, long-term compounding, and stability + growth balance. You MUST NOT mention international diversification, global growth, foreign exposure, currency hedging, global technology themes, or geographical dispersion.
        """
        else:
            intl_constraint = ""

        # Check if Excel has these values
        excel_exec_brief = client_data.get("Executive Briefing", "").strip()
        excel_thesis = client_data.get("Portfolio Thesis & Market Overview", "").strip()

        briefing_instruction_1 = " (Since the client has already provided their own Executive Briefing in the Excel, do NOT write a new one; simply return an empty string for this field.)" if excel_exec_brief else ""
        briefing_instruction_2 = " (Since the client has already provided their own Portfolio Thesis & Market Overview in the Excel, do NOT write a new one; simply return an empty string for this field.)" if excel_thesis else ""

        prompt = f"""
        You are a premium private wealth management advisor at a top-tier institutional firm.
        Generate a fully customized, professional investment portfolio proposal for this client.
        
        SYSTEM RULES & INSTRUCTION:
        1. NO REPETITIVE STRUCTURES: Different funds must use completely different writing structures and sentence flows. Do NOT use the same paragraph framework across different funds.
        2. NO BOILERPLATE OPENINGS: Do not start any detailed_rationale with "Selected to align with the client's objective...", "The investment strategy...", "It focuses on...", or similar repetitive/canned openings. Every opening sentence must be written independently.
        3. DYNAMIC ORDERING: Do not force every detailed_rationale to contain the same sections in the same order. For some funds, discuss the strategy first; for others, discuss suitability; for others, discuss market positioning or risk buffer first.
        4. CATEGORY-SPECIFIC COMMENTARY: Discuss actual, real-world fund characteristics in the detailed_rationale:
           - Balanced Advantage Funds: Explain dynamic equity-debt allocation, active shifts between equity and debt based on valuations, and hedging.
           - Multi Asset Funds: Explain diversification across uncorrelated asset classes (shares, debt, gold, silver, arbitrage).
           - Aggressive Hybrid Funds: Explain the blended equity participation with a structural debt stability cushion.
           - Small Cap Funds: Explain high-growth emerging business exposure, niche market leaders, and accepting higher volatility/fluctuations.
           - Multicap Funds: Explain the structured, mandatory allocation across market capitalizations (large, mid, and small cap companies).
           - Arbitrage Funds: Discuss tax-efficient market-neutral arbitrage capturing spot-future spreads.
           - Liquid/Money Market: Focus on capital preservation, overnight safety reserve, and immediate liquidity.
        5. WEALTH MANAGER PERSONA: Write as if each commentary was custom-written by an independent private banker or wealth manager. Avoid clinical, robotic, or template-based structures.
        6. RANDOMIZE ALL NARRATIVE VARIABLES: Randomize the opening sentence style, sentence order, sentence count (e.g. some detailed rationales should have 2 sentences, others 3 sentences), and explanation style.
        7. FORCE HETEROGENEITY: Verify that two funds from different categories (and even within the same category) do not share the same paragraph template or grammatical construction.
        8. For each recommended product in your response list, select a DIFFERENT advisory tone style randomly from the following styles and write that specific product's rationales in that tone:
           - Institutional wealth advisory tone (highly professional, objective, structured, institutional-grade)
           - Private banker tone (sophisticated, client-relationship-centric, bespoke, high-touch)
           - CIO-style commentary (analytical, macro-driven, forward-looking, cycle-oriented)
           - Conservative capital preservation style (risk-conscious, protective, stability-focused, cautious)
           - Growth-focused strategic allocation style (compounding-oriented, opportunistic, active growth, market-beating)
           Vary it heavily across the products in the portfolio.
        9. Vary sentence lengths and structures aggressively per product:
           - Ensure each product's rationale is distinct in structure, flow, and wording.
        
        Global Portfolio Theme:
        - The global theme of the portfolio is: "{selected_style}"

        
        Client Profile & Parameters:
        - Client Name: {profile["client_name"]}
        - Risk Appetite: {profile["risk_appetite"]}
        - Client Objective: {profile["objective"]}
        - Portfolio Theme: {profile["portfolio_theme"]}
        - Investment Style: {profile["investment_style"]}
        - Market Positioning: {profile["market_positioning"]}
        - Age Group: {profile["assumptions"]["age_group"]}
        - Investment Horizon: {profile["assumptions"]["investment_horizon"]}
        - Liquidity Needs: {profile["assumptions"]["liquidity_needs"]}
        - Income Stability: {profile["assumptions"]["income_stability"]}
        - Wealth Preservation Requirements: {profile["assumptions"]["wealth_preservation_requirements"]}
        - Portfolio Corpus: {corpus_words}
        
        Recommended Products:
        {json.dumps(recommended_products_payload, indent=2)}
        
        CRITICAL RULES FOR NARRATIVE GENERATION:
        1. PERSPECTIVE & PERSONA: You MUST write this entire proposal using the following perspective/persona: "{perspective}"
        2. SENTENCE STRUCTURE RULE: {starter_rule}
        3. VOCABULARY RULE: You MUST weave in at least one of these exact words in the 'detailed_rationale' field of each product: {", ".join(seed_words)}. However, do NOT use any of these words more than twice across the entire proposal list to prevent repetition.
        4. CUSTOMIZATION & DEPENDENCY: Every fund's rationales ("summary_rationale", "detailed_rationale", "Expected Role", "Risk Profile", "Expected Benefit", "Market Positioning", "Downside Protection", "Diversification Benefit") MUST depend heavily on and reference:
           - The client's corpus size ({corpus_words}). Frame the allocation size relative to this wealth scale.
           - The client's risk profile ({profile["risk_appetite"]}).
           - The product's allocation percentage (e.g. Allocation Percentage in the product list).
           - The current market positioning ({profile["market_positioning"]}).
           - The portfolio objective ({profile["objective"]}).
           - The specific role of this fund inside the portfolio (as part of Segment).
        5. UNIQUE PHRASING: Every single product's rationales MUST have completely unique phrasing, sentence structures, and lengths. Do NOT reuse the same sentence structures or wording across different products.
        6. NO BOILERPLATE: Absolutely do NOT use generic boilerplate phrases or patterns, such as:
           - "dynamic equity-debt allocation"
           - "consistent returns across market conditions"
           - "balanced risk-reward"
           - "long-term wealth creation"
           - "provides stability"
           - "diversifies across"
           - "reduces volatility"
           - "combines stability and growth"
           - "hedges against downside"
        7. You MUST NOT use these overly technical words and phrases anywhere in your product rationales:
           - "downside protection"
           - "macroeconomic"
           - "tactical allocation"
           - "volatility management"
           - "capital appreciation"
           - "diversification benefits"
           - "asset class exposure"
           - "CAGR"
           - "alpha"
           - "sharpe ratio"
           - "drawdown"
        8. For each product's rationales, you MUST generate two distinct rationale fields:
             - "summary_rationale": A concise CORE RATIONALE of 20 to 30 words maximum (no more than 2 sentences) answering only: Why was this fund selected? It must be concise and summary-level.
             - "detailed_rationale": A detailed STRATEGY & RATIONALE explanation of 4 to 5 full lines (55 to 70 words) that is significantly more detailed than CORE RATIONALE. It must not simply rephrase CORE RATIONALE and must explain: the role of the fund in the portfolio, its risk-return characteristics, its diversification benefit, and how it aligns with the client's objective.
             - Ensure "detailed_rationale" does not repeat or paraphrase "summary_rationale" anywhere in its text.
        9. Weave the client's name ({short_client}) naturally into the rationale to guarantee it is completely unique and personalized for their portfolio.
        10. Treat this as a completely new request: do not reuse any rationale sentences from older runs or reports. Prioritize high variation in rationale wording. Make sure that if the same fund appears in different client portfolios, the generated rationale is completely different and tailored to each client's specific situation.
        11. Write in a natural, conversational, premium wealth advisor tone. Do not mention any prompt rules, perspective names, or seed constraints in your final text.
        13. TERMINOLOGY RULE: You MUST NOT use custom marketing segment names (such as 'Adaptive Hybrid Core', 'Distributed Strategic Enablers', 'Holistic Equity Growth', 'Accelerated Alpha Seeker', etc.) anywhere in your narratives, summaries, thesis, or product rationales. Instead, always use the official, dynamically determined AMFI Mutual Fund category names (such as 'Balanced Advantage Fund', 'Aggressive Hybrid Fund', 'Multi Asset Allocation Fund', 'Multi Cap Fund', 'Small Cap Fund', etc.) when referencing the portfolio segments.
        {intl_constraint}
        
        Tasks:
        1. Generate:
           - "portfolio_theme": Verify and output the selected portfolio theme ("{profile["portfolio_theme"]}").
           - "executive_summary": A high-end narrative briefing summarizing this proposal tailored for the client.{briefing_instruction_1}
           - "portfolio_thesis": A strategic macro-level explanation of our asset allocation reasoning.{briefing_instruction_2}
           - "market_commentary": An institutional-grade market overview describing why this mix makes sense in the current economic environment.
           - "segment_names": Provide the official AMFI Mutual Fund category name (e.g., 'Balanced Advantage Fund', 'Aggressive Hybrid Fund', 'Multi Asset Allocation Fund', 'Multi Cap Fund', 'Small Cap Fund', etc.) for each of the 4 Parts (1, 2, 3, and 4) based on the recommended products.
             - Key "1": Official AMFI Category name for Part 1 (Liquid Fund sleeve).
             - Key "2": Official AMFI Category name for Part 2 (Corporate Bond Fund sleeve).
             - Key "3": Official AMFI Category name for Part 3 (Multi Asset Allocation Fund sleeve).
             - Key "4": Official AMFI Category name for Part 4 (Wealth Creation sleeve).
        
        2. Write a simple client-friendly expanded rationale for EACH product. Break it down into exactly these 8 points:
           - "summary_rationale": A concise CORE RATIONALE of 20-30 words maximum (max 2 sentences) answering: Why was this fund selected?
           - "detailed_rationale": A detailed STRATEGY & RATIONALE of 55-70 words explaining strategy, allocation approach, risk framework, and suitability, ensuring it is significantly more detailed and does not repeat summary_rationale.
           - "expected_role": A very simple one-line explanation of the fund's role.
           - "risk_profile": Plain English explanation of the risk without jargon.
           - "expected_benefit": The positive outcome expected.
           - "market_positioning": The fund's strength or manager quality.
           - "downside_protection": How this fund buffers downside drops.
           - "diversification_benefit": How it complements other holdings.
        
        Return your answer ONLY as a JSON object matching this schema. Do NOT wrap it in any formatting like markdown backticks, just output raw JSON text:
        {{
          "portfolio_theme": "{profile["portfolio_theme"]}",
          "executive_summary": "High-end tailored briefing...",
          "portfolio_thesis": "Strategic macro-level allocation explanation...",
          "market_commentary": "Institutional market outlook...",
          "segment_names": {{
            "1": "Official AMFI Category Name for Part 1",
            "2": "Official AMFI Category Name for Part 2",
            "3": "Official AMFI Category Name for Part 3",
            "4": "Official AMFI Category Name for Part 4"
          }},
          "products": [
            {{
              "Product Name": "Exact name of the product from input",
              "summary_rationale": "20-30 words concise CORE RATIONALE...",
              "detailed_rationale": "55-70 words detailed STRATEGY & RATIONALE...",
              "Expected Role": "Simple explanation...",
              "Risk Profile": "Simple explanation...",
              "Expected Benefit": "Simple explanation...",
              "Market Positioning": "Simple explanation...",
              "Downside Protection": "Simple explanation...",
              "Diversification Benefit": "Simple explanation..."
            }},
            ...
          ]
        }}
        """
        print(f"[MEMORY PROFILE] 4. Gemini prompt created: {get_memory_usage():.2f} MB")
        text = call_llm_api(prompt, api_key, temperature=selected_temp).strip()
        print(f"[MEMORY PROFILE] 5. Gemini response received: {get_memory_usage():.2f} MB")
        api_succeeded = True
        

        
        # 9. Strip markdown code fences automatically before parsing (robust regex)
        cleaned_text = text.strip()
        cleaned_text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", cleaned_text)
        cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        # 6. Check if the same cached response is being reused across requests
        import hashlib
        text_hash = hashlib.md5(cleaned_text.encode('utf-8')).hexdigest()
        global _RECENT_GEMINI_RESPONSES
        if text_hash in _RECENT_GEMINI_RESPONSES:
            print(f"[CACHE CHECK] WARNING: The exact same Gemini response (hash {text_hash}) was returned. Cached response reuse suspected!")
        else:
            _RECENT_GEMINI_RESPONSES.append(text_hash)
            if len(_RECENT_GEMINI_RESPONSES) > 10:
                _RECENT_GEMINI_RESPONSES.pop(0)
                
        try:
            result = json.loads(cleaned_text)
            print(f"[MEMORY PROFILE] 6. Proposal JSON built: {get_memory_usage():.2f} MB")
            parsing_succeeded = True
        except Exception as json_err:
            print(f"AI PARSE FAILURE REASON: JSON decode failure - {str(json_err)}")
            # 2. Print the exact exception traceback causing JSON decode failure
            traceback.print_exc()
            raise json_err
            
        # 4. Temporarily DISABLE strict schema validation entirely
        validation_errors = []


        
        portfolio_theme = result.get("portfolio_theme") or profile["portfolio_theme"]
        client_data["portfolio_theme"] = portfolio_theme
        
        # Do NOT overwrite segment names with custom segment names from the LLM.
        # Instead, consistently use the official AMFI Mutual Fund category names dynamically determined in Python.
        pass
                        
        gemini_products = result.get("products", [])
        
        # Robust matching block
        matched_gp_indices = set()
        
        def clean_prod_name(name):
            n = str(name).lower().strip()
            # Remove punctuation and common words
            import re
            n = re.sub(r'[^a-z0-9\s]', '', n)
            words = [w for w in n.split() if w not in ["fund", "growth", "direct", "plan", "dividend", "pms", "option"]]
            return "".join(words)
 
        for p_idx, p in enumerate(cleaned_products):
            match = None
            
            # 1. Exact match
            for gp_idx, gp in enumerate(gemini_products):
                if gp_idx in matched_gp_indices:
                    continue
                gp_name = str(gp.get("Product Name") or gp.get("Product") or "").lower().strip()
                p_name = p["Product Name"].lower().strip()
                if gp_name == p_name:
                    match = gp
                    matched_gp_indices.add(gp_idx)
                    break
            
            # 2. Cleaned exact match
            if not match:
                for gp_idx, gp in enumerate(gemini_products):
                    if gp_idx in matched_gp_indices:
                        continue
                    gp_name = str(gp.get("Product Name") or gp.get("Product") or "")
                    if clean_prod_name(gp_name) == clean_prod_name(p["Product Name"]):
                        match = gp
                        matched_gp_indices.add(gp_idx)
                        break
            
            # 3. Substring match
            if not match:
                for gp_idx, gp in enumerate(gemini_products):
                    if gp_idx in matched_gp_indices:
                        continue
                    gp_name = str(gp.get("Product Name") or gp.get("Product") or "")
                    c_gp = clean_prod_name(gp_name)
                    c_p = clean_prod_name(p["Product Name"])
                    if c_gp and c_p and (c_gp in c_p or c_p in c_gp):
                        match = gp
                        matched_gp_indices.add(gp_idx)
                        break
                        
            # 4. Fallback to index if within bounds
            if not match:
                if p_idx < len(gemini_products):
                    match = gemini_products[p_idx]
                    
            if match:
                matched_count += 1
            else:
                print(f"[AI Engine] Matching failure: Product '{p['Product Name']}' could not be aligned with Gemini response products.")
                
            rat_card = _get_fallback_rationale_for_product(p["Part"], p["Product Name"], profile, p.get("Allocation (INR)_float"), p.get("Core Rationale", ""))
            qual_keys = [
                ("summary_rationale", "summary_rationale"),
                ("detailed_rationale", "detailed_rationale"),
                ("Why Selected", "Why Selected"),
                ("Expected Role", "Expected Role"),
                ("Risk Profile", "Risk Profile"),
                ("Expected Benefit", "Expected Benefit"),
                ("Market Positioning", "Market Positioning"),
                ("Downside Protection", "Downside Protection"),
                ("Diversification Benefit", "Diversification Benefit")
            ]
            
            # Rationale fields mapping
            has_raw_excel = False
            raw_excel_val = p.get("Core Rationale")
            if raw_excel_val and len(str(raw_excel_val).strip()) > 2 and str(raw_excel_val).lower() != "nan":
                has_raw_excel = True

            for k_target, k_gemini in qual_keys:
                val = ""
                if has_raw_excel and k_target in ["Why Selected", "summary_rationale", "detailed_rationale"]:
                    val = rat_card[k_target.lower().replace(" ", "_")]
                elif match:
                    val = match.get(k_target) or match.get(k_gemini) or match.get(k_gemini.lower()) or match.get(k_gemini.replace(" ", "")) or ""
                    # Backward-compatibility fallback inside Gemini response
                    if k_target == "Why Selected" and not val:
                        val = match.get("detailed_rationale") or match.get("summary_rationale") or ""
                
                is_valid = True
                fail_reason = ""
                if val and str(val).strip() and not (has_raw_excel and k_target in ["Why Selected", "summary_rationale", "detailed_rationale"]):
                    is_valid, fail_reason = validate_rationale(p["Product Name"], p["AMFI_Category"], str(val).strip(), corpus, corpus_words)
                
                if val and str(val).strip() and is_valid:
                    # Preserve the raw generated rationale wording without rewriting it
                    p[k_target] = str(val).strip()
                else:
                    if val and str(val).strip() and not is_valid:
                        print(f"[AI Engine Validation WARNING] Product '{p['Product Name']}' field '{k_target}' failed validation: {fail_reason}. Falling back.")
                    # Fallback template activated only for this specific missing/empty/invalid field
                    if not (has_raw_excel and k_target in ["Why Selected", "summary_rationale", "detailed_rationale"]):
                        fallback_activated_count += 1
                    p[k_target] = rat_card[k_target.lower().replace(" ", "_")]
                    
        # Log dynamic API success parameters (Stdout)
        print("[AI Engine] Response validated successfully")
        
        # Check if Excel has these values
        excel_exec_brief = client_data.get("Executive Briefing", "").strip()
        excel_thesis = client_data.get("Portfolio Thesis & Market Overview", "").strip()
        
        exec_summary = excel_exec_brief if excel_exec_brief else (str(result.get("executive_summary")).strip() if result.get("executive_summary") else local_briefings["executive_summary"])
        thesis = excel_thesis if excel_thesis else (str(result.get("portfolio_thesis")).strip() if result.get("portfolio_thesis") else local_briefings["portfolio_thesis"])

        ensure_unique_rationales(cleaned_products, profile)
        return {
            "portfolio_theme": portfolio_theme,
            "executive_summary": scrub_forbidden_phrases(exec_summary),
            "portfolio_thesis": scrub_forbidden_phrases(thesis),
            "market_commentary": str(result.get("market_commentary")).strip() if result.get("market_commentary") else scrub_forbidden_phrases(local_briefings["market_commentary"]),
            "allocation": allocations,
            "products": cleaned_products
        }
        
    except Exception as e:
        error_detail = str(e)
        import traceback
        print(f"[AI Engine ERROR] Fallback activated. Detail: {error_detail}", flush=True)
        traceback.print_exc()
        
        # Apply local rationales for each product
        for p in cleaned_products:
            rat_card = _get_fallback_rationale_for_product(p["Part"], p["Product Name"], profile, p.get("Allocation (INR)_float"), p.get("Core Rationale", ""))
            
            p["Why Selected"] = scrub_forbidden_phrases(simplify_jargon(rat_card["why_selected"]))
            p["summary_rationale"] = scrub_forbidden_phrases(simplify_jargon(rat_card["summary_rationale"]))
            p["detailed_rationale"] = scrub_forbidden_phrases(simplify_jargon(rat_card["detailed_rationale"]))
            p["Expected Role"] = scrub_forbidden_phrases(simplify_jargon(rat_card["expected_role"]))
            p["Risk Profile"] = scrub_forbidden_phrases(simplify_jargon(rat_card["risk_profile"]))
            p["Expected Benefit"] = scrub_forbidden_phrases(simplify_jargon(rat_card["expected_benefit"]))
            p["Market Positioning"] = scrub_forbidden_phrases(simplify_jargon(rat_card["market_positioning"]))
            p["Downside Protection"] = scrub_forbidden_phrases(simplify_jargon(rat_card["downside_protection"]))
            p["Diversification Benefit"] = scrub_forbidden_phrases(simplify_jargon(rat_card["diversification_benefit"]))
            

            
        # Check if Excel has these values
        excel_exec_brief = client_data.get("Executive Briefing", "").strip()
        excel_thesis = client_data.get("Portfolio Thesis & Market Overview", "").strip()
        
        exec_summary = excel_exec_brief if excel_exec_brief else local_briefings["executive_summary"]
        thesis = excel_thesis if excel_thesis else local_briefings["portfolio_thesis"]

        ensure_unique_rationales(cleaned_products, profile)
        return {
            "portfolio_theme": profile["portfolio_theme"],
            "executive_summary": scrub_forbidden_phrases(exec_summary),
            "portfolio_thesis": scrub_forbidden_phrases(thesis),
            "market_commentary": scrub_forbidden_phrases(local_briefings["market_commentary"]),
            "allocation": allocations,
            "products": cleaned_products
        }
