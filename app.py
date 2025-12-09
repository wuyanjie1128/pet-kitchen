import os
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st
import altair as alt


# =========================
# Nebula Paw Kitchen - Theme
# =========================

APP_TITLE = "Nebula Paw Kitchen™"
APP_SUBTITLE = "Premium Fresh Meal Intelligence for Dogs"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🐶🍲",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
.stApp {
    background:
        radial-gradient(1200px 800px at 10% 10%, rgba(120, 140, 255, 0.16), transparent 60%),
        radial-gradient(1200px 800px at 90% 20%, rgba(255, 120, 220, 0.12), transparent 60%),
        radial-gradient(900px 700px at 20% 90%, rgba(120, 255, 200, 0.10), transparent 60%),
        linear-gradient(135deg, #070812 0%, #0a0c1a 40%, #0a0b14 100%);
    color: #F5F7FF;
}
h1, h2, h3, h4 { letter-spacing: 0.4px; }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    border-right: 1px solid rgba(255,255,255,0.06);
}
.nebula-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 18px 18px 12px 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}
.nebula-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.12), transparent);
    margin: 14px 0 18px 0;
}
.stButton > button {
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.10);
    background: linear-gradient(135deg, rgba(120,140,255,0.20), rgba(255,120,220,0.18));
    color: white;
    font-weight: 600;
}
.stButton > button:hover {
    border: 1px solid rgba(255,255,255,0.25);
    transform: translateY(-1px);
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    background-color: rgba(255,255,255,0.04) !important;
    border-radius: 10px;
}
thead tr th { background-color: rgba(255,255,255,0.06) !important; }
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.10);
    margin-left: 6px;
}
.small-muted { opacity: 0.8; font-size: 0.9rem; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================
# Breed Database
# =========================

@st.cache_data
def load_breeds() -> pd.DataFrame:
    path = os.path.join("data", "breeds.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
    else:
        # Minimal fallback to avoid runtime failure
        df = pd.DataFrame([
            {"Breed": "Mixed Breed / Unknown", "FCI Group": "N/A", "Region": "Global", "Size Class": "Unknown", "Notes": ""},
            {"Breed": "Labrador Retriever", "FCI Group": "Group 8 - Retrievers, Flushing Dogs, Water Dogs", "Region": "Europe", "Size Class": "Large", "Notes": ""},
            {"Breed": "German Shepherd Dog", "FCI Group": "Group 1 - Sheepdogs and Cattle Dogs", "Region": "Europe", "Size Class": "Large", "Notes": ""},
            {"Breed": "Shiba Inu", "FCI Group": "Group 5 - Spitz and Primitive types", "Region": "Asia", "Size Class": "Medium", "Notes": ""},
        ])

    # Normalize columns
    for col in ["Breed", "FCI Group", "Region", "Size Class", "Notes"]:
        if col not in df.columns:
            df[col] = ""

    df["Breed"] = df["Breed"].astype(str).str.strip()
    df["FCI Group"] = df["FCI Group"].astype(str).str.strip()
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Size Class"] = df["Size Class"].astype(str).str.strip()

    # Ensure Mixed Breed exists
    if not (df["Breed"] == "Mixed Breed / Unknown").any():
        df = pd.concat([pd.DataFrame([{
            "Breed": "Mixed Breed / Unknown",
            "FCI Group": "N/A",
            "Region": "Global",
            "Size Class": "Unknown",
            "Notes": ""
        }]), df], ignore_index=True)

    # De-duplicate
    df = df.drop_duplicates(subset=["Breed"]).sort_values("Breed").reset_index(drop=True)
    return df


BREED_DF = load_breeds()

BREED_LIST = BREED_DF["Breed"].tolist()
BREED_META = BREED_DF.set_index("Breed").to_dict(orient="index")


def filter_breed_options(
    search: str,
    fci_groups: List[str],
    regions: List[str],
    sizes: List[str],
) -> List[str]:
    df = BREED_DF.copy()

    if fci_groups:
        df = df[df["FCI Group"].isin(fci_groups)]
    if regions:
        df = df[df["Region"].isin(regions)]
    if sizes:
        df = df[df["Size Class"].isin(sizes)]
    if search.strip():
        s = search.strip().lower()
        mask = (
            df["Breed"].str.lower().str.contains(s, na=False) |
            df["Notes"].astype(str).str.lower().str.contains(s, na=False)
        )
        df = df[mask]

    opts = df["Breed"].tolist()
    if not opts:
        opts = ["Mixed Breed / Unknown"]
    return opts


# =========================
# Ingredient Knowledge Base
# =========================

@dataclass(frozen=True)
class Ingredient:
    name: str
    category: str  # Meat, Veg, Carb, Oil, Treat
    kcal_per_100g: float
    protein_g: float
    fat_g: float
    carbs_g: float
    micronote: str
    benefits: List[str]
    cautions: List[str]


@dataclass(frozen=True)
class RatioPreset:
    key: str
    label: str
    meat_pct: int
    veg_pct: int
    carb_pct: int
    note: str


def build_ingredients() -> Dict[str, Ingredient]:
    items = [
        # --- Meats / Proteins ---
        Ingredient("Chicken (lean, cooked)", "Meat", 165, 31, 3.6, 0,
                   "B vitamins, selenium.",
                   ["High-quality protein for muscle maintenance", "Generally well tolerated", "Excellent base protein for rotation"],
                   ["Avoid if chicken allergy suspected", "Remove skin for lower-fat plans"]),
        Ingredient("Turkey (lean, cooked)", "Meat", 150, 29, 2.0, 0,
                   "Niacin, selenium.",
                   ["Lean protein option", "Great for weight-aware plans", "Mild flavor"],
                   ["Avoid processed/deli products"]),
        Ingredient("Beef (lean, cooked)", "Meat", 200, 26, 10, 0,
                   "Iron, zinc, B12.",
                   ["Supports red blood cell health", "Strong palatability", "Good for active adults"],
                   ["Higher fat depending on cut"]),
        Ingredient("Lamb (lean, cooked)", "Meat", 206, 25, 12, 0,
                   "Zinc, carnitine.",
                   ["Alternative protein", "Rich taste for picky dogs", "Useful rotation option"],
                   ["Can be richer; adjust for pancreatitis risk"]),
        Ingredient("Pork (lean, cooked)", "Meat", 195, 27, 9, 0,
                   "Thiamine-rich protein.",
                   ["Good rotation variety", "Often highly palatable", "Supports energy metabolism"],
                   ["Use lean cuts; avoid processed pork"]),
        Ingredient("Duck (lean, cooked)", "Meat", 190, 24, 11, 0,
                   "Rich flavor, B vitamins.",
                   ["Great for variety", "High palatability", "Useful to prevent boredom"],
                   ["Moderate fat"]),
        Ingredient("Venison (lean, cooked)", "Meat", 158, 30, 3.2, 0,
                   "Often considered novel protein.",
                   ["Lean novel option", "Rotation diversity", "Good for some sensitive dogs"],
                   ["Novel protein strategies should be vet-guided"]),
        Ingredient("Rabbit (cooked)", "Meat", 173, 33, 3.5, 0,
                   "Very lean, novel option.",
                   ["Lean and light", "Excellent rotation diversity"],
                   ["Ensure safe sourcing"]),
        Ingredient("Egg (cooked)", "Meat", 155, 13, 11, 1.1,
                   "Complete amino acid profile.",
                   ["Top-tier protein quality", "Palatability booster"],
                   ["Introduce gradually"]),
        Ingredient("Salmon (cooked)", "Meat", 208, 20, 13, 0,
                   "Omega-3, vitamin D.",
                   ["Skin/coat support", "Anti-inflammatory profile", "Good for seniors"],
                   ["Higher fat; portion carefully"]),
        Ingredient("White Fish (cod, cooked)", "Meat", 105, 23, 0.9, 0,
                   "Very lean protein.",
                   ["Excellent for weight plans", "Gentle for GI-sensitive dogs"],
                   ["Keep it plain"]),
        Ingredient("Sardines (cooked, deboned)", "Meat", 208, 25, 11, 0,
                   "Omega-3 rich mini-fish.",
                   ["Great topper for coat/joints", "Very palatable"],
                   ["Watch sodium if canned"]),

        # --- Vegetables ---
        Ingredient("Pumpkin (cooked)", "Veg", 26, 1, 0.1, 6.5,
                   "Soluble fiber + beta-carotene.",
                   ["Supports stool quality", "Great transition veggie", "Gentle gut support"],
                   ["Too much can dilute calories"]),
        Ingredient("Carrot (cooked)", "Veg", 35, 0.8, 0.2, 8,
                   "Beta-carotene.",
                   ["Antioxidant support", "Low calorie micronutrient boost"],
                   ["Chop/soften for tiny breeds"]),
        Ingredient("Broccoli (cooked)", "Veg", 34, 2.8, 0.4, 7,
                   "Vitamin C, K.",
                   ["Rotation-friendly antioxidants", "Good micronutrient diversity"],
                   ["Large amounts may cause gas"]),
        Ingredient("Zucchini (cooked)", "Veg", 17, 1.2, 0.3, 3.1,
                   "Hydration-friendly veggie.",
                   ["Great for volumizing meals", "Mild taste"],
                   ["Avoid seasoning"]),
        Ingredient("Green Beans (cooked)", "Veg", 31, 1.8, 0.1, 7,
                   "Low-calorie bulk.",
                   ["Helpful for weight management", "Gentle fiber"],
                   []),
        Ingredient("Cauliflower (cooked)", "Veg", 25, 1.9, 0.3, 5,
                   "Low-cal crucifer.",
                   ["Adds volume", "Good rotation veggie"],
                   ["May cause gas"]),
        Ingredient("Sweet Peas (cooked)", "Veg", 84, 5.4, 0.4, 15.6,
                   "Plant protein + fiber.",
                   ["Adds variety", "Good texture mix-in"],
                   ["Moderate starch"]),
        Ingredient("Kale (cooked, small portions)", "Veg", 35, 2.9, 1.5, 4.4,
                   "Dense micronutrients.",
                   ["Small-dose antioxidant boost"],
                   ["Use small portions"]),
        Ingredient("Spinach (cooked, small portions)", "Veg", 23, 2.9, 0.4, 3.6,
                   "Folate, magnesium.",
                   ["Micronutrient variety"],
                   ["Use small portions due to oxalates"]),
        Ingredient("Bell Pepper (red, cooked)", "Veg", 31, 1, 0.3, 6,
                   "Colorful vitamin-rich veggie.",
                   ["Adds antioxidant color diversity"],
                   ["Avoid spicy/seasoned"]),
        Ingredient("Cabbage (cooked, small portions)", "Veg", 23, 1.3, 0.1, 5.5,
                   "Budget-friendly fiber.",
                   ["Adds variety"],
                   ["May cause gas"]),
        Ingredient("Cucumber (peeled, small portions)", "Veg", 15, 0.7, 0.1, 3.6,
                   "Hydrating crunch.",
                   ["Cooling low-cal add-on"],
                   ["Chop small"]),

        # --- Carbs ---
        Ingredient("Sweet Potato (cooked)", "Carb", 86, 1.6, 0.1, 20,
                   "Beta-carotene, potassium.",
                   ["Palatable energy base", "Great controlled carb"],
                   ["Portion for weight control"]),
        Ingredient("Brown Rice (cooked)", "Carb", 123, 2.7, 1.0, 25.6,
                   "Gentle starch base.",
                   ["Neutral, easy-to-digest"],
                   ["Lower if overweight/diabetic plan"]),
        Ingredient("White Rice (cooked)", "Carb", 130, 2.4, 0.3, 28.2,
                   "Very gentle GI carb.",
                   ["Useful during sensitive stomach phases"],
                   ["Lower micronutrients vs brown rice"]),
        Ingredient("Oats (cooked)", "Carb", 71, 2.5, 1.4, 12,
                   "Soluble fiber.",
                   ["Satiety support", "Gut-friendly option"],
                   ["Introduce gradually"]),
        Ingredient("Quinoa (cooked)", "Carb", 120, 4.4, 1.9, 21.3,
                   "Higher protein carb.",
                   ["Adds amino acid diversity"],
                   ["Rinse well before cooking"]),
        Ingredient("Barley (cooked)", "Carb", 123, 2.3, 0.4, 28,
                   "Fiber-rich grain.",
                   ["Satiety-friendly carb"],
                   ["Introduce gradually"]),
        Ingredient("Buckwheat (cooked)", "Carb", 92, 3.4, 0.6, 19.9,
                   "Alternative pseudo-grain.",
                   ["Variety option"],
                   ["Cook thoroughly"]),
        Ingredient("Potato (cooked, plain)", "Carb", 87, 2, 0.1, 20,
                   "Simple starch.",
                   ["Palatable limited-ingredient carb"],
                   ["Never raw; avoid green parts"]),

        # --- Oils ---
        Ingredient("Fish Oil (supplemental)", "Oil", 900, 0, 100, 0,
                   "EPA/DHA omega-3s.",
                   ["Skin/coat support", "Joint and inflammatory support"],
                   ["Dose carefully"]),
        Ingredient("Olive Oil (small amounts)", "Oil", 884, 0, 100, 0,
                   "Monounsaturated fats.",
                   ["Palatability booster"],
                   ["Too much may trigger GI upset"]),
        Ingredient("Flaxseed Oil (small amounts)", "Oil", 884, 0, 100, 0,
                   "ALA omega-3 (plant-based).",
                   ["Rotation fat option"],
                   ["ALA conversion to EPA/DHA is limited"]),
        Ingredient("MCT Oil (very small amounts)", "Oil", 900, 0, 100, 0,
                   "Specialized fat.",
                   ["Occasional vet-guided senior cognition support"],
                   ["Can cause diarrhea"]),

        # --- Treat / Fruits ---
        Ingredient("Blueberries (small portions)", "Treat", 57, 0.7, 0.3, 14.5,
                   "Antioxidant fruit topper.",
                   ["Small antioxidant boost", "Fun topper variety"],
                   ["Use small portions"]),
        Ingredient("Apple (peeled, no seeds)", "Treat", 52, 0.3, 0.2, 14,
                   "Hydrating sweet crunch.",
                   ["Low-cal treat topper"],
                   ["Remove seeds/core"]),
        Ingredient("Strawberries (small portions)", "Treat", 32, 0.7, 0.3, 7.7,
                   "Vitamin C + flavor variety.",
                   ["Light fruity enrichment"],
                   ["Use small portions"]),
    ]
    return {i.name: i for i in items}


INGREDIENTS = build_ingredients()


# =========================
# Life stage & energy helpers
# =========================

def age_to_life_stage(age_years: float) -> str:
    if age_years < 1:
        return "Puppy"
    if age_years < 7:
        return "Adult"
    return "Senior"


def calc_rer(weight_kg: float) -> float:
    return 70 * (weight_kg ** 0.75)


def mer_factor(life_stage: str, activity: str, neutered: bool) -> float:
    base = 1.6 if neutered else 1.8
    if life_stage == "Puppy":
        base = 2.2 if neutered else 2.4
    elif life_stage == "Senior":
        base = 1.3 if neutered else 1.4

    activity_boost = {
        "Low": 0.9,
        "Normal": 1.0,
        "High": 1.2,
        "Athletic/Working": 1.35,
    }.get(activity, 1.0)

    return base * activity_boost


# =========================
# Ratio Presets
# =========================

RATIO_PRESETS = [
    RatioPreset("balanced", "Balanced Cooked Fresh (default)", 50, 35, 15,
                "A practical cooked-fresh ratio emphasizing lean protein and diverse vegetables."),
    RatioPreset("weight", "Weight-Aware & Satiety", 45, 45, 10,
                "Higher vegetable volume and slightly reduced energy density."),
    RatioPreset("active", "Active Adult Energy", 55, 25, 20,
                "More energy support for high activity while keeping vegetables present."),
    RatioPreset("senior", "Senior Gentle Balance", 48, 40, 12,
                "Fiber and micronutrient focus, moderate carbs."),
    RatioPreset("puppy", "Puppy Growth (cooked baseline)", 55, 30, 15,
                "Growth needs are complex; ensure calcium/vitamin balance with veterinary guidance."),
    RatioPreset("gentle_gi", "Gentle GI Rotation", 50, 40, 10,
                "A calmer profile leaning on easy proteins and soothing fiber veggies."),
]


# =========================
# Supplements (expanded)
# =========================

SUPPLEMENTS = [
    {"name": "Omega-3 (Fish Oil)",
     "why": "Supports skin/coat, joint comfort, and inflammatory balance.",
     "best_for": ["Dry/itchy skin", "Senior dogs", "Joint support plans"],
     "cautions": "Dose carefully; may loosen stool. Check with vet if on clotting-related meds.",
     "pairing": "Pairs well with lean proteins and antioxidant-rich vegetables."},

    {"name": "Probiotics",
     "why": "May improve gut resilience and stool stability.",
     "best_for": ["Sensitive stomach", "Diet transitions", "Stress-related GI changes"],
     "cautions": "Choose canine-specific options.",
     "pairing": "Works nicely with pumpkin, oats, and gentle proteins."},

    {"name": "Prebiotic Fiber (e.g., inulin, MOS)",
     "why": "Supports beneficial gut bacteria and stool quality.",
     "best_for": ["Soft stools", "Gut resilience goals"],
     "cautions": "Too much can cause gas.",
     "pairing": "Often paired with probiotics."},

    {"name": "Calcium Support (for home-cooked)",
     "why": "Home-cooked diets commonly need calcium balancing.",
     "best_for": ["Puppies", "Long-term cooked routines"],
     "cautions": "Over/under supplementation can be risky—vet nutritionist advised.",
     "pairing": "Essential when meals are fully home-prepared."},

    {"name": "Canine Multivitamin",
     "why": "Helps cover micronutrient gaps in simplified recipes.",
     "best_for": ["Limited ingredient variety", "Long-term home cooking"],
     "cautions": "Avoid human multivitamins unless approved.",
     "pairing": "Best with weekly rotation."},

    {"name": "Joint Support (Glucosamine/Chondroitin/UC-II)",
     "why": "May support mobility and cartilage health.",
     "best_for": ["Large breeds", "Senior dogs", "Highly active dogs"],
     "cautions": "Effects vary and take time.",
     "pairing": "Pairs with omega-3 and weight control."},

    {"name": "Vitamin E (as guided)",
     "why": "Antioxidant support often used alongside omega-3.",
     "best_for": ["Dogs on long-term fish oil"],
     "cautions": "Avoid excessive dosing.",
     "pairing": "Consider with fatty acid protocols."},

    {"name": "Dental Additives (vet-approved)",
     "why": "Helps reduce plaque when brushing is difficult.",
     "best_for": ["Small breeds", "Dental-prone dogs"],
     "cautions": "Not a substitute for brushing.",
     "pairing": "Pair with safe chewing strategies."},

    {"name": "L-Carnitine (vet-guided)",
     "why": "May assist some weight or cardiac strategies.",
     "best_for": ["Vet-supervised weight plans"],
     "cautions": "Use under professional advice.",
     "pairing": "Best with lean protein + veggie-heavy ratios."},
]


# =========================
# Core data utilities
# =========================

def ingredient_df() -> pd.DataFrame:
    rows = []
    for ing in INGREDIENTS.values():
        rows.append({
            "Ingredient": ing.name,
            "Category": ing.category,
            "kcal/100g": ing.kcal_per_100g,
            "Protein(g)": ing.protein_g,
            "Fat(g)": ing.fat_g,
            "Carbs(g)": ing.carbs_g,
            "Micro-note": ing.micronote,
            "Benefits": " • ".join(ing.benefits),
            "Cautions": " • ".join(ing.cautions) if ing.cautions else "",
        })
    df = pd.DataFrame(rows)
    return df.sort_values(["Category", "Ingredient"]).reset_index(drop=True)


def filter_ingredients_by_category(cat: str) -> List[str]:
    return [i.name for i in INGREDIENTS.values() if i.category == cat]


def compute_daily_energy(
    weight_kg: float,
    age_years: float,
    activity: str,
    neutered: bool,
    special_flags: List[str]
) -> Tuple[float, float, float, str]:
    stage = age_to_life_stage(age_years)
    rer = calc_rer(weight_kg)
    mer = rer * mer_factor(stage, activity, neutered)

    adj = 1.0
    rationale = []

    if "Overweight / Weight loss goal" in special_flags:
        adj *= 0.85
        rationale.append("Weight-loss adjusted target.")
    if "Pancreatitis risk / Needs lower fat" in special_flags:
        adj *= 0.95
        rationale.append("Fat-sensitive conservative target.")
    if "Kidney concern (vet-managed)" in special_flags:
        adj *= 0.95
        rationale.append("Energy conservative; protein strategy must be vet-guided.")
    if "Very picky eater" in special_flags:
        rationale.append("Use palatability tactics & stronger rotation.")

    mer_adj = mer * adj
    explanation = stage + (" | " + " ".join(rationale) if rationale else "")

    return rer, mer, mer_adj, explanation


def ensure_ratio_sum(meat_pct: int, veg_pct: int, carb_pct: int) -> Tuple[int, int, int]:
    total = meat_pct + veg_pct + carb_pct
    if total == 100:
        return meat_pct, veg_pct, carb_pct
    meat = round(meat_pct / total * 100)
    veg = round(veg_pct / total * 100)
    carb = 100 - meat - veg
    carb = max(0, carb)
    if meat + veg + carb != 100:
        diff = 100 - (meat + veg + carb)
        meat = max(0, meat + diff)
    return meat, veg, carb


def estimate_food_grams_from_energy(daily_kcal: float, assumed_kcal_per_g: float) -> float:
    return daily_kcal / assumed_kcal_per_g


def grams_for_day(total_grams: float, meat_pct: int, veg_pct: int, carb_pct: int) -> Tuple[float, float, float]:
    return (
        total_grams * meat_pct / 100,
        total_grams * veg_pct / 100,
        total_grams * carb_pct / 100
    )


def day_nutrition_estimate(meat: str, veg: str, carb: str,
                           meat_g: float, veg_g: float, carb_g: float) -> Dict[str, float]:
    def calc(name: str, grams: float) -> Dict[str, float]:
        ing = INGREDIENTS[name]
        f = grams / 100.0
        return {
            "kcal": ing.kcal_per_100g * f,
            "protein": ing.protein_g * f,
            "fat": ing.fat_g * f,
            "carbs": ing.carbs_g * f,
        }
    a, b, c = calc(meat, meat_g), calc(veg, veg_g), calc(carb, carb_g)
    return {
        "kcal": a["kcal"] + b["kcal"] + c["kcal"],
        "protein": a["protein"] + b["protein"] + c["protein"],
        "fat": a["fat"] + b["fat"] + c["fat"],
        "carbs": a["carbs"] + b["carbs"] + c["carbs"],
    }


# =========================
# Recommender
# =========================

def recommend_ingredients(stage: str, special_flags: List[str]) -> Dict[str, List[str]]:
    meats, vegs, carbs, treats = [], [], [], []

    base_meats = [
        "Turkey (lean, cooked)", "White Fish (cod, cooked)",
        "Salmon (cooked)", "Egg (cooked)", "Lamb (lean, cooked)"
    ]
    base_vegs = [
        "Pumpkin (cooked)", "Zucchini (cooked)",
        "Green Beans (cooked)", "Carrot (cooked)", "Bell Pepper (red, cooked)"
    ]
    base_carbs = [
        "Sweet Potato (cooked)", "Brown Rice (cooked)",
        "Oats (cooked)", "Quinoa (cooked)"
    ]
    base_treats = [
        "Blueberries (small portions)", "Apple (peeled, no seeds)", "Strawberries (small portions)"
    ]

    meats.extend(base_meats)
    vegs.extend(base_vegs)
    carbs.extend(base_carbs)
    treats.extend(base_treats)

    if stage == "Puppy":
        meats.extend(["Chicken (lean, cooked)", "Beef (lean, cooked)"])
        carbs.extend(["White Rice (cooked)"])
        vegs.extend(["Pumpkin (cooked)"])
    elif stage == "Senior":
        meats.extend(["White Fish (cod, cooked)", "Salmon (cooked)"])
        vegs.extend(["Pumpkin (cooked)", "Zucchini (cooked)"])

    if "Sensitive stomach" in special_flags:
        meats.extend(["Turkey (lean, cooked)", "White Fish (cod, cooked)"])
        vegs.extend(["Pumpkin (cooked)"])
        carbs.extend(["White Rice (cooked)", "Oats (cooked)"])

    if "Skin/coat concern" in special_flags:
        meats.extend(["Salmon (cooked)", "Sardines (cooked, deboned)"])
        treats.extend(["Blueberries (small portions)"])

    if "Overweight / Weight loss goal" in special_flags:
        meats.extend(["Turkey (lean, cooked)", "White Fish (cod, cooked)", "Rabbit (cooked)"])
        vegs.extend(["Green Beans (cooked)", "Zucchini (cooked)", "Cauliflower (cooked)"])

    if "Pancreatitis risk / Needs lower fat" in special_flags:
        meats = [m for m in meats if m not in ["Salmon (cooked)", "Duck (lean, cooked)", "Sardines (cooked, deboned)"]]
        meats.extend(["Turkey (lean, cooked)", "White Fish (cod, cooked)"])

    def dedupe(lst):
        seen, out = set(), []
        for x in lst:
            if x in INGREDIENTS and x not in seen:
                out.append(x)
                seen.add(x)
        return out

    return {"Meat": dedupe(meats), "Veg": dedupe(vegs), "Carb": dedupe(carbs), "Treat": dedupe(treats)}


# =========================
# Taste learning (multi-dog)
# =========================

def pref_score_from_label(p: str) -> int:
    return {"Dislike": 0, "Neutral": 1, "Like": 2, "Love": 3}.get(p, 1)


def get_preference_maps(dog_id: str) -> Tuple[Dict[str, float], Dict[str, float]]:
    entries = [e for e in st.session_state.taste_log if e.get("dog_id") == dog_id]
    if not entries:
        return {}, {}
    df = pd.DataFrame(entries)
    if df.empty:
        return {}, {}
    df["score"] = df["Preference"].map(pref_score_from_label)

    protein_map, veg_map = {}, {}
    sub = df.dropna(subset=["Protein"])
    if not sub.empty:
        protein_map = sub.groupby("Protein")["score"].mean().to_dict()
    sub = df.dropna(subset=["Veg"])
    if not sub.empty:
        veg_map = sub.groupby("Veg")["score"].mean().to_dict()

    return protein_map, veg_map


def weighted_choice(rng: random.Random, items: List[str], weights: List[float]) -> str:
    if not items:
        raise ValueError("weighted_choice received empty items")
    if len(items) != len(weights):
        raise ValueError("weighted_choice items/weights length mismatch")
    total = sum(max(0.0, w) for w in weights)
    if total <= 0:
        return rng.choice(items)
    r = rng.random() * total
    acc = 0.0
    for item, w in zip(items, weights):
        w = max(0.0, w)
        acc += w
        if r <= acc:
            return item
    return items[-1]


def pick_rotation_smart(
    pantry_meats: List[str],
    pantry_vegs: List[str],
    pantry_carbs: List[str],
    allow_new: bool,
    recommendations: Dict[str, List[str]],
    taste_meat_map: Dict[str, float],
    taste_veg_map: Dict[str, float],
    use_taste_weights: bool,
    days: int = 7,
    seed: Optional[int] = None
) -> List[Dict[str, str]]:
    rng = random.Random(seed if seed is not None else 42)

    all_meats = filter_ingredients_by_category("Meat")
    all_vegs = filter_ingredients_by_category("Veg")
    all_carbs = filter_ingredients_by_category("Carb")

    if allow_new:
        meat_pool = list(dict.fromkeys(pantry_meats + recommendations.get("Meat", []) + all_meats))
        veg_pool = list(dict.fromkeys(pantry_vegs + recommendations.get("Veg", []) + all_vegs))
        carb_pool = list(dict.fromkeys(pantry_carbs + recommendations.get("Carb", []) + all_carbs))
    else:
        meat_pool = pantry_meats if pantry_meats else all_meats
        veg_pool = pantry_vegs if pantry_vegs else all_vegs
        carb_pool = pantry_carbs if pantry_carbs else all_carbs

    def taste_weight(name: str, m: Dict[str, float]) -> float:
        if not use_taste_weights:
            return 1.0
        s = m.get(name)
        if s is None:
            return 1.0
        return max(0.25, 0.25 + float(s))  # 0..3 -> 0.25..3.25

    def choose(pool: List[str], last: Optional[str], last2: Optional[str], taste_map: Dict[str, float]) -> str:
        if not pool:
            return rng.choice(all_meats)

        candidates = pool[:]
        if last and last2 and last == last2:
            filtered = [x for x in candidates if x != last]
            if filtered:
                candidates = filtered
        if last and len(candidates) > 1:
            filtered = [x for x in candidates if x != last]
            if filtered:
                candidates = filtered

        weights = [taste_weight(x, taste_map) for x in candidates]
        return weighted_choice(rng, candidates, weights)

    plan = []
    last_meat = last_meat2 = None
    last_veg = last_veg2 = None

    for _ in range(days):
        meat = choose(meat_pool, last_meat, last_meat2, taste_meat_map)
        veg = choose(veg_pool, last_veg, last_veg2, taste_veg_map) if veg_pool else rng.choice(all_vegs)
        carb = rng.choice(carb_pool) if carb_pool else rng.choice(all_carbs)

        plan.append({"Meat": meat, "Veg": veg, "Carb": carb})

        last_meat2, last_meat = last_meat, meat
        last_veg2, last_veg = last_veg, veg

    return plan


def build_weekly_shopping_list(plan_df: pd.DataFrame) -> pd.DataFrame:
    totals = {}

    def add_item(name: str, grams: float):
        if not name or name == "—":
            return
        totals[name] = totals.get(name, 0.0) + float(grams)

    for _, row in plan_df.iterrows():
        add_item(row.get("Meat"), row.get("Daily Meat (g)", 0))
        add_item(row.get("Veg"), row.get("Daily Veg (g)", 0))
        add_item(row.get("Carb"), row.get("Daily Carb (g)", 0))

    rows = []
    for name, g in totals.items():
        cat = INGREDIENTS.get(name).category if name in INGREDIENTS else "Unknown"
        rows.append({
            "Ingredient": name,
            "Category": cat,
            "Total grams (7 days)": round(g),
            "Avg grams/day": round(g / 7.0, 1),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["Category", "Ingredient"]).reset_index(drop=True)


def build_category_prep_summary(shopping_df: pd.DataFrame) -> pd.DataFrame:
    if shopping_df.empty:
        return shopping_df
    grp = shopping_df.groupby("Category")["Total grams (7 days)"].sum().reset_index()
    grp["Total grams (7 days)"] = grp["Total grams (7 days)"].round().astype(int)
    return grp.sort_values("Total grams (7 days)", ascending=False).reset_index(drop=True)


# =========================
# Multi-dog session
# =========================

def default_dog_profile(dog_id: str) -> Dict:
    return {
        "id": dog_id,
        "name": "",
        "breed": "Mixed Breed / Unknown",
        "age_years": 3.0,
        "weight_kg": 10.0,
        "neutered": True,
        "activity": "Normal",
        "special_flags": ["None"],
        "meals_per_day": 2,
        "assumed_kcal_per_g": 1.35,
    }


def dog_display_name(d: Dict, idx: int) -> str:
    nm = (d.get("name") or "").strip()
    return nm if nm else f"Dog {idx}"


if "dogs" not in st.session_state:
    st.session_state.dogs = [default_dog_profile("dog-1")]

if "active_dog_id" not in st.session_state:
    st.session_state.active_dog_id = st.session_state.dogs[0]["id"]

if "taste_log" not in st.session_state:
    st.session_state.taste_log = []  # entries with dog_id


def get_active_dog() -> Dict:
    for d in st.session_state.dogs:
        if d["id"] == st.session_state.active_dog_id:
            return d
    st.session_state.active_dog_id = st.session_state.dogs[0]["id"]
    return st.session_state.dogs[0]


def update_active_dog(updates: Dict):
    for i, d in enumerate(st.session_state.dogs):
        if d["id"] == st.session_state.active_dog_id:
            new_d = d.copy()
            new_d.update(updates)
            st.session_state.dogs[i] = new_d
            return


# =========================
# Sidebar - Multi-dog control + Breed filters
# =========================

st.sidebar.markdown(f"## 🐶🍳 {APP_TITLE}")
st.sidebar.caption("Cosmic-grade cooked fresh meal intelligence")

dog_labels = [dog_display_name(d, i + 1) for i, d in enumerate(st.session_state.dogs)]
label_to_id = {dog_labels[i]: st.session_state.dogs[i]["id"] for i in range(len(st.session_state.dogs))}

selected_label = st.sidebar.selectbox("Select dog profile", dog_labels, index=0)
st.session_state.active_dog_id = label_to_id[selected_label]
active_dog = get_active_dog()

with st.sidebar.expander("➕ Add new dog profile", expanded=False):
    new_name = st.text_input("New dog name", value="", key="new_dog_name")

    st.markdown("**Breed Atlas filters**")
    new_search = st.text_input("Search", value="", key="new_breed_search")
    new_fci = st.multiselect("FCI Group", sorted(BREED_DF["FCI Group"].unique().tolist()), default=[], key="new_breed_fci")
    new_region = st.multiselect("Region", sorted(BREED_DF["Region"].unique().tolist()), default=[], key="new_breed_region")
    new_size = st.multiselect("Size class", sorted(BREED_DF["Size Class"].unique().tolist()), default=[], key="new_breed_size")

    new_options = filter_breed_options(new_search, new_fci, new_region, new_size)
    new_breed = st.selectbox("New dog breed", new_options, index=0, key="new_dog_breed")

    new_age = st.number_input("New dog age (years)", 0.1, 25.0, 2.0, 0.1, key="new_dog_age")
    new_weight = st.number_input("New dog weight (kg)", 0.5, 90.0, 8.0, 0.1, key="new_dog_weight")
    new_neut = st.toggle("Neutered/Spayed", True, key="new_dog_neut")
    new_act = st.select_slider("Activity level", ["Low", "Normal", "High", "Athletic/Working"], value="Normal", key="new_dog_act")
    new_flags = st.multiselect(
        "Special considerations",
        [
            "None",
            "Overweight / Weight loss goal",
            "Sensitive stomach",
            "Pancreatitis risk / Needs lower fat",
            "Skin/coat concern",
            "Very picky eater",
            "Kidney concern (vet-managed)",
            "Food allergy suspected",
            "Joint/mobility support focus",
        ],
        default=["None"],
        key="new_dog_flags"
    )
    if "None" in new_flags and len(new_flags) > 1:
        new_flags = [f for f in new_flags if f != "None"]

    new_meals = st.select_slider("Meals per day", [1, 2, 3, 4], value=2, key="new_dog_meals")
    new_density = st.slider("Assumed energy density (kcal/g)", 1.0, 1.8, 1.35, 0.05, key="new_dog_density")

    if st.button("Create profile", key="create_profile_btn"):
        new_id = f"dog-{len(st.session_state.dogs) + 1}"
        d = default_dog_profile(new_id)
        d.update({
            "name": new_name.strip(),
            "breed": new_breed,
            "age_years": float(new_age),
            "weight_kg": float(new_weight),
            "neutered": bool(new_neut),
            "activity": new_act,
            "special_flags": new_flags if new_flags else ["None"],
            "meals_per_day": int(new_meals),
            "assumed_kcal_per_g": float(new_density),
        })
        st.session_state.dogs.append(d)
        st.session_state.active_dog_id = new_id
        st.success("New dog profile added!")

st.sidebar.markdown("---")
st.sidebar.markdown("### Edit active profile")

dog_name = st.sidebar.text_input("Dog name", value=active_dog.get("name", ""))

st.sidebar.markdown("**Breed Atlas filters**")
breed_search = st.sidebar.text_input("Search", value="", key="breed_search_active")
breed_fci = st.sidebar.multiselect("FCI Group", sorted(BREED_DF["FCI Group"].unique().tolist()), default=[], key="breed_fci_active")
breed_region = st.sidebar.multiselect("Region", sorted(BREED_DF["Region"].unique().tolist()), default=[], key="breed_region_active")
breed_size = st.sidebar.multiselect("Size class", sorted(BREED_DF["Size Class"].unique().tolist()), default=[], key="breed_size_active")

breed_options = filter_breed_options(breed_search, breed_fci, breed_region, breed_size)

current_breed = active_dog.get("breed", "Mixed Breed / Unknown")
if current_breed not in breed_options:
    breed_options = [current_breed] + breed_options

breed = st.sidebar.selectbox("Breed", breed_options, index=breed_options.index(current_breed))

col_a, col_b = st.sidebar.columns(2)
with col_a:
    age_years = st.sidebar.number_input("Age (years)", 0.1, 25.0, float(active_dog.get("age_years", 3.0)), 0.1)
with col_b:
    weight_kg = st.sidebar.number_input("Weight (kg)", 0.5, 90.0, float(active_dog.get("weight_kg", 10.0)), 0.1)

neutered = st.sidebar.toggle("Neutered/Spayed", value=bool(active_dog.get("neutered", True)))
activity = st.sidebar.select_slider("Activity level", ["Low", "Normal", "High", "Athletic/Working"],
                                    value=active_dog.get("activity", "Normal"))

special_flags = st.sidebar.multiselect(
    "Special considerations",
    [
        "None",
        "Overweight / Weight loss goal",
        "Sensitive stomach",
        "Pancreatitis risk / Needs lower fat",
        "Skin/coat concern",
        "Very picky eater",
        "Kidney concern (vet-managed)",
        "Food allergy suspected",
        "Joint/mobility support focus",
    ],
    default=active_dog.get("special_flags", ["None"])
)
if "None" in special_flags and len(special_flags) > 1:
    special_flags = [f for f in special_flags if f != "None"]

meals_per_day = st.sidebar.select_slider("Meals per day", [1, 2, 3, 4], value=int(active_dog.get("meals_per_day", 2)))

assumed_kcal_per_g = st.sidebar.slider(
    "Assumed energy density (kcal per gram of cooked mix)",
    1.0, 1.8, float(active_dog.get("assumed_kcal_per_g", 1.35)), 0.05
)

if st.sidebar.button("Save profile changes"):
    update_active_dog({
        "name": dog_name.strip(),
        "breed": breed,
        "age_years": float(age_years),
        "weight_kg": float(weight_kg),
        "neutered": bool(neutered),
        "activity": activity,
        "special_flags": special_flags if special_flags else ["None"],
        "meals_per_day": int(meals_per_day),
        "assumed_kcal_per_g": float(assumed_kcal_per_g),
    })
    st.sidebar.success("Profile updated!")

st.sidebar.markdown("---")
st.sidebar.caption("Educational tool; not a substitute for veterinary nutrition advice.")


# =========================
# Top Banner
# =========================

title_name = dog_name.strip() or "Your dog"

st.markdown(
    f"""
    <div class="nebula-card">
      <h1>🐶🍲 {APP_TITLE}</h1>
      <p style="font-size: 1.05rem; opacity: 0.9;">
        {APP_SUBTITLE}
        <span class="badge">Cooked Fresh Focus</span>
        <span class="badge">Breed Atlas</span>
        <span class="badge">Multi-dog Mode</span>
        <span class="badge">Taste-learning</span>
      </p>
      <div class="nebula-divider"></div>
      <p style="opacity: 0.9;">
        A high-end, rotation-based cooked fresh planner for <b>{title_name}</b>.
        Explore ingredient science, build weekly menus, and let preferences shape the next week.
      </p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# Tabs
# =========================

tab_home, tab_ingredients, tab_ratio, tab_planner, tab_supp, tab_feedback = st.tabs(
    [
        "🐶🍳 Command Deck",
        "🥩🥦 Ingredient Cosmos",
        "⚖️ Ratio Lab",
        "📅 7-Day Intelligent Plan",
        "💊 Supplement Observatory",
        "😋 Taste & Notes"
    ]
)


# =========================
# 1) Command Deck
# =========================

with tab_home:
    st.markdown("### Dog Profile Snapshot")

    stage = age_to_life_stage(age_years)
    meta = BREED_META.get(breed, {})
    size_class = meta.get("Size Class", "Unknown")
    region = meta.get("Region", "Unknown")
    fci_group = meta.get("FCI Group", "Unknown")

    rer, mer, mer_adj, explanation = compute_daily_energy(
        weight_kg=weight_kg,
        age_years=age_years,
        activity=activity,
        neutered=neutered,
        special_flags=special_flags
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Name", title_name)
    c2.metric("Life stage", stage)
    c3.metric("RER (kcal/day)", f"{rer:.0f}")
    c4.metric("Target MER (adjusted)", f"{mer_adj:.0f}")

    st.caption(f"Breed: {breed} · Size class: {size_class} · Region: {region}")
    st.caption(f"FCI classification: {fci_group}")
    st.caption(f"Meals/day: {meals_per_day}")
    st.caption(f"Context note: {explanation}")

    with st.expander("Breed Atlas table (filtered view)"):
        st.dataframe(BREED_DF, use_container_width=True, height=320)

    st.markdown("### Safety-first cooking principles")
    with st.expander("Open safety notes (important)"):
        st.write(
            """
            - This tool is designed for **cooked fresh meal inspiration**.
            - Avoid seasoning (salt, onion, garlic, spicy sauces).
            - Ensure proteins are fully cooked and deboned.
            - Long-term home-cooked feeding typically needs **calcium + micronutrient balancing**.
            - Medical conditions require a vet or veterinary nutritionist plan.
            """
        )


# =========================
# 2) Ingredient Cosmos
# =========================

with tab_ingredients:
    st.markdown("### Ingredient Encyclopedia")

    df = ingredient_df()

    col_f1, col_f2, col_f3 = st.columns([1.2, 1.2, 2])
    with col_f1:
        cat_filter = st.selectbox("Category filter", ["All", "Meat", "Veg", "Carb", "Oil", "Treat"])
    with col_f2:
        sort_key = st.selectbox("Sort by", ["Category", "Ingredient", "kcal/100g", "Protein(g)", "Fat(g)", "Carbs(g)"])
    with col_f3:
        search_text = st.text_input("Search ingredient name or notes", value="")

    df_view = df.copy()
    if cat_filter != "All":
        df_view = df_view[df_view["Category"] == cat_filter]

    if search_text.strip():
        mask = (
            df_view["Ingredient"].str.contains(search_text, case=False, na=False) |
            df_view["Micro-note"].str.contains(search_text, case=False, na=False) |
            df_view["Benefits"].str.contains(search_text, case=False, na=False)
        )
        df_view = df_view[mask]

    df_view = df_view.sort_values(sort_key).reset_index(drop=True)
    st.dataframe(df_view, use_container_width=True, height=360)

    st.markdown("### Deep-dive cards (text-only)")
    selected_ing = st.selectbox("Pick an ingredient to explore", df["Ingredient"].tolist())
    ing_obj = INGREDIENTS[selected_ing]

    st.markdown(
        f"""
        <div class="nebula-card">
          <h3>{ing_obj.name}</h3>
          <p><b>Category:</b> {ing_obj.category}</p>
          <p><b>Approx nutrition (per 100g cooked):</b>
             {ing_obj.kcal_per_100g:.0f} kcal ·
             P {ing_obj.protein_g:.1f}g ·
             F {ing_obj.fat_g:.1f}g ·
             C {ing_obj.carbs_g:.1f}g
          </p>
          <p><b>Micro-note:</b> {ing_obj.micronote}</p>
          <div class="nebula-divider"></div>
          <p><b>Benefits</b></p>
          <ul>
            {''.join([f'<li>{b}</li>' for b in ing_obj.benefits])}
          </ul>
          <p><b>Cautions</b></p>
          <ul>
            {''.join([f'<li>{c}</li>' for c in ing_obj.cautions]) if ing_obj.cautions else '<li>No major general cautions listed for standard cooked use.</li>'}
          </ul>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# 3) Ratio Lab
# =========================

with tab_ratio:
    st.markdown("### Ratio Presets and Custom Physics")

    preset_labels = {p.label: p.key for p in RATIO_PRESETS}
    preset_choice_label = st.selectbox("Choose a ratio preset", list(preset_labels.keys()))
    preset_key = preset_labels[preset_choice_label]
    preset_obj = next(p for p in RATIO_PRESETS if p.key == preset_key)

    st.info(preset_obj.note)

    use_custom = st.toggle("Override with custom ratios", value=False)

    if not use_custom:
        meat_pct, veg_pct, carb_pct = preset_obj.meat_pct, preset_obj.veg_pct, preset_obj.carb_pct
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            meat_pct = st.slider("Meat %", 30, 70, preset_obj.meat_pct)
        with c2:
            veg_pct = st.slider("Veg %", 15, 55, preset_obj.veg_pct)
        with c3:
            carb_pct = st.slider("Carb %", 0, 30, preset_obj.carb_pct)
        meat_pct, veg_pct, carb_pct = ensure_ratio_sum(meat_pct, veg_pct, carb_pct)
        st.caption(f"Normalized ratio: Meat {meat_pct}% · Veg {veg_pct}% · Carb {carb_pct}%")

    stage = age_to_life_stage(age_years)
    rer, mer, mer_adj, explanation = compute_daily_energy(
        weight_kg=weight_kg, age_years=age_years, activity=activity,
        neutered=neutered, special_flags=special_flags
    )

    daily_grams = estimate_food_grams_from_energy(mer_adj, assumed_kcal_per_g)
    meat_g, veg_g, carb_g = grams_for_day(daily_grams, meat_pct, veg_pct, carb_pct)

    st.markdown("### Daily gram target (based on your energy assumptions)")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Total cooked mix (g/day)", f"{daily_grams:.0f}")
    g2.metric("Meat target (g)", f"{meat_g:.0f}")
    g3.metric("Veg target (g)", f"{veg_g:.0f}")
    g4.metric("Carb target (g)", f"{carb_g:.0f}")

    st.markdown("### Macro energy lens (conceptual)")
    cat_means = ingredient_df().groupby("Category")[["kcal/100g"]].mean()

    def est_cat_kcal(cat: str, grams: float) -> float:
        if cat not in cat_means.index:
            return 0.0
        return float(cat_means.loc[cat, "kcal/100g"]) * grams / 100.0

    ratio_kcal_df = pd.DataFrame([
        {"Component": "Meat (avg)", "kcal": est_cat_kcal("Meat", meat_g)},
        {"Component": "Veg (avg)", "kcal": est_cat_kcal("Veg", veg_g)},
        {"Component": "Carb (avg)", "kcal": est_cat_kcal("Carb", carb_g)},
    ])

    chart = (
        alt.Chart(ratio_kcal_df)
        .mark_arc(innerRadius=50)
        .encode(
            theta="kcal:Q",
            color="Component:N",
            tooltip=["Component", alt.Tooltip("kcal:Q", format=".0f")]
        )
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)


# =========================
# 4) 7-Day Intelligent Plan
# =========================

with tab_planner:
    st.markdown("### Pantry-driven weekly generation")

    all_meats = filter_ingredients_by_category("Meat")
    all_vegs = filter_ingredients_by_category("Veg")
    all_carbs = filter_ingredients_by_category("Carb")

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        pantry_meats = st.multiselect("Meats you have", all_meats, default=[])
    with col_p2:
        pantry_vegs = st.multiselect("Vegetables you have", all_vegs, default=[])
    with col_p3:
        pantry_carbs = st.multiselect("Carbs you have", all_carbs, default=[])

    st.markdown("### Human-friendly planning style")

    col_mode1, col_mode2, col_mode3, col_mode4 = st.columns([1.1, 1.1, 1.2, 1.6])
    with col_mode1:
        pantry_only = st.toggle("Pantry-only mode", value=False,
                                help="Strictly uses selected pantry items (fallback to all if empty).")
    with col_mode2:
        allow_new = st.toggle("Smart rotation mode", value=True,
                              help="Allows new ingredients for variety and boredom prevention.")
    with col_mode3:
        taste_mode = st.toggle("Taste-informed rotation", value=True,
                               help="Uses your taste log to bias next week toward favorites.")
    with col_mode4:
        include_fruit_toppers = st.toggle("Allow fruit toppers (small)", value=True,
                                          help="Adds small optional fruit suggestions.")

    stage = age_to_life_stage(age_years)
    recs = recommend_ingredients(stage, special_flags)

    st.markdown("### What we recommend adding (personalized)")
    rr1, rr2, rr3, rr4 = st.columns(4)
    with rr1:
        st.write("**Proteins**")
        st.write("\n".join([f"• {x}" for x in recs["Meat"][:8]]) if recs["Meat"] else "—")
    with rr2:
        st.write("**Vegetables**")
        st.write("\n".join([f"• {x}" for x in recs["Veg"][:8]]) if recs["Veg"] else "—")
    with rr3:
        st.write("**Carbs**")
        st.write("\n".join([f"• {x}" for x in recs["Carb"][:8]]) if recs["Carb"] else "—")
    with rr4:
        st.write("**Fruits (optional small)**")
        if include_fruit_toppers and recs["Treat"]:
            st.write("\n".join([f"• {x}" for x in recs["Treat"][:6]]))
        else:
            st.write("—")

    st.markdown("### Ratio configuration for the planner")

    preset_labels = {p.label: p.key for p in RATIO_PRESETS}
    planner_preset_label = st.selectbox("Planner ratio preset", list(preset_labels.keys()), index=0)
    planner_preset_key = preset_labels[planner_preset_label]
    planner_preset_obj = next(p for p in RATIO_PRESETS if p.key == planner_preset_key)

    planner_custom = st.toggle("Fine-tune planner ratio", value=False)

    if not planner_custom:
        meat_pct, veg_pct, carb_pct = planner_preset_obj.meat_pct, planner_preset_obj.veg_pct, planner_preset_obj.carb_pct
    else:
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            meat_pct = st.slider("Planner Meat %", 30, 70, planner_preset_obj.meat_pct, key="planner_meat")
        with cc2:
            veg_pct = st.slider("Planner Veg %", 15, 55, planner_preset_obj.veg_pct, key="planner_veg")
        with cc3:
            carb_pct = st.slider("Planner Carb %", 0, 30, planner_preset_obj.carb_pct, key="planner_carb")
        meat_pct, veg_pct, carb_pct = ensure_ratio_sum(meat_pct, veg_pct, carb_pct)

    rer, mer, mer_adj, explanation = compute_daily_energy(
        weight_kg=weight_kg, age_years=age_years, activity=activity,
        neutered=neutered, special_flags=special_flags
    )

    daily_grams = estimate_food_grams_from_energy(mer_adj, assumed_kcal_per_g)
    meat_g, veg_g, carb_g = grams_for_day(daily_grams, meat_pct, veg_pct, carb_pct)

    st.caption(
        f"Daily targets (assumption-based): "
        f"{daily_grams:.0f}g total → Meat {meat_g:.0f}g · Veg {veg_g:.0f}g · Carb {carb_g:.0f}g"
    )
    st.caption(f"Meals/day: {meals_per_day} → per-meal split will be shown in the plan.")

    seed = st.slider("Rotation randomness seed", 1, 999, 42,
                     help="Change this to reshuffle the weekly rotation.")
    generate = st.button("✨ Generate 7-Day Nebula Plan")

    effective_allow_new = (allow_new and not pantry_only)
    taste_meat_map, taste_veg_map = get_preference_maps(st.session_state.active_dog_id)

    if generate:
        rotation = pick_rotation_smart(
            pantry_meats=pantry_meats,
            pantry_vegs=pantry_vegs,
            pantry_carbs=pantry_carbs,
            allow_new=effective_allow_new,
            recommendations=recs,
            taste_meat_map=taste_meat_map,
            taste_veg_map=taste_veg_map,
            use_taste_weights=taste_mode,
            days=7,
            seed=seed
        )

        fruit_rotation = []
        if include_fruit_toppers and recs["Treat"]:
            rng = random.Random(seed + 7)
            for _ in range(7):
                fruit_rotation.append(rng.choice(recs["Treat"]))
        else:
            fruit_rotation = [None] * 7

        per_meal_total = daily_grams / meals_per_day
        per_meal_meat = meat_g / meals_per_day
        per_meal_veg = veg_g / meals_per_day
        per_meal_carb = carb_g / meals_per_day

        rows = []
        for i, combo in enumerate(rotation, start=1):
            mg, vg, cg = grams_for_day(daily_grams, meat_pct, veg_pct, carb_pct)
            nut = day_nutrition_estimate(combo["Meat"], combo["Veg"], combo["Carb"], mg, vg, cg)

            rows.append({
                "Day": f"Day {i}",
                "Meat": combo["Meat"],
                "Veg": combo["Veg"],
                "Carb": combo["Carb"],
                "Optional Fruit Topper": fruit_rotation[i-1] or "—",
                "Daily Meat (g)": round(mg),
                "Daily Veg (g)": round(vg),
                "Daily Carb (g)": round(cg),
                "Per-Meal Total (g)": round(per_meal_total),
                "Per-Meal Meat (g)": round(per_meal_meat),
                "Per-Meal Veg (g)": round(per_meal_veg),
                "Per-Meal Carb (g)": round(per_meal_carb),
                "Est kcal": round(nut["kcal"]),
                "Protein (g)": round(nut["protein"], 1),
                "Fat (g)": round(nut["fat"], 1),
                "Carbs (g)": round(nut["carbs"], 1),
            })

        plan_df = pd.DataFrame(rows)

        st.markdown(f"### {title_name}'s weekly plan")
        st.dataframe(plan_df, use_container_width=True, height=360)

        st.markdown("### Weekly nutrient trend (approx)")
        melt = plan_df.melt(
            id_vars=["Day"],
            value_vars=["Est kcal", "Protein (g)", "Fat (g)", "Carbs (g)"],
            var_name="Metric",
            value_name="Value"
        )
        line = (
            alt.Chart(melt)
            .mark_line(point=True)
            .encode(
                x="Day:N",
                y="Value:Q",
                color="Metric:N",
                tooltip=["Day", "Metric", "Value"]
            )
            .properties(height=260)
        )
        st.altair_chart(line, use_container_width=True)

        st.markdown("### 🧾 Weekly shopping list & batch-prep calculator")
        shopping_df = build_weekly_shopping_list(plan_df)
        if shopping_df.empty:
            st.info("Shopping list is empty (unexpected). Try regenerating the plan.")
        else:
            cat_summary = build_category_prep_summary(shopping_df)

            csum1, csum2 = st.columns([1, 2])
            with csum1:
                st.markdown("**Category totals**")
                st.dataframe(cat_summary, use_container_width=True, height=220)
            with csum2:
                st.markdown("**Ingredient totals (7 days)**")
                st.dataframe(shopping_df, use_container_width=True, height=220)

            csv_bytes = shopping_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download shopping list (CSV)",
                data=csv_bytes,
                file_name=f"{title_name.lower().replace(' ', '_')}_shopping_list.csv",
                mime="text/csv"
            )


# =========================
# 5) Supplement Observatory
# =========================

with tab_supp:
    st.markdown("### Conservative supplement pairing guide")

    st.markdown(
        """
        Supplements can help fill gaps in simplified cooked diets,
        but the best strategy depends on your dog's health.
        This section provides **non-prescriptive** educational guidance.
        """
    )

    supp_df = pd.DataFrame(SUPPLEMENTS)
    st.dataframe(
        supp_df[["name", "why", "cautions", "pairing"]],
        use_container_width=True,
        height=280
    )

    st.markdown("### Personalized supplement lens")
    focus = st.multiselect(
        "What do you want to prioritize?",
        ["Skin/Coat", "Gut", "Joint/Mobility", "Puppy Growth Support",
         "Senior Vitality", "Weight Management", "Dental Support"],
        default=[]
    )

    def add_if(lst, item):
        if item not in lst:
            lst.append(item)

    suggestions = []
    if "Skin/Coat" in focus:
        add_if(suggestions, "Omega-3 (Fish Oil)")
        add_if(suggestions, "Vitamin E (as guided)")
    if "Gut" in focus:
        add_if(suggestions, "Probiotics")
        add_if(suggestions, "Prebiotic Fiber (e.g., inulin, MOS)")
    if "Joint/Mobility" in focus:
        add_if(suggestions, "Joint Support (Glucosamine/Chondroitin/UC-II)")
        add_if(suggestions, "Omega-3 (Fish Oil)")
    if "Puppy Growth Support" in focus:
        add_if(suggestions, "Calcium Support (for home-cooked)")
        add_if(suggestions, "Canine Multivitamin")
    if "Senior Vitality" in focus:
        add_if(suggestions, "Omega-3 (Fish Oil)")
        add_if(suggestions, "Joint Support (Glucosamine/Chondroitin/UC-II)")
        add_if(suggestions, "Probiotics")
    if "Weight Management" in focus:
        add_if(suggestions, "Probiotics")
        add_if(suggestions, "L-Carnitine (vet-guided)")
    if "Dental Support" in focus:
        add_if(suggestions, "Dental Additives (vet-approved)")

    if suggestions:
        st.markdown(
            f"""
            <div class="nebula-card">
              <h4>Suggested educational focus</h4>
              <ul>
                {''.join([f'<li>{s}</li>' for s in suggestions])}
              </ul>
              <div class="nebula-divider"></div>
              <p class="small-muted">
                For dosing and long-term protocols, confirm with a veterinarian,
                especially if your dog has a medical condition or takes medication.
              </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.caption("Select a priority to see a conservative educational highlight list.")


# =========================
# 6) Taste & Notes (per-dog)
# =========================

with tab_feedback:
    st.markdown(f"### Taste tracking capsule for {title_name}")

    st.write(
        """
        Record how your dog responds to different proteins and vegetables.
        This log stays in your session and helps the next week's planner learn preferences.
        """
    )

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        log_meat = st.selectbox("Observed protein", ["(skip)"] + filter_ingredients_by_category("Meat"))
    with col_t2:
        log_veg = st.selectbox("Observed vegetable", ["(skip)"] + filter_ingredients_by_category("Veg"))
    with col_t3:
        love_level = st.select_slider(
            "Preference",
            options=["Dislike", "Neutral", "Like", "Love"],
            value="Like"
        )

    notes = st.text_input("Optional notes (stool, energy, itching, etc.)")

    if st.button("🧪 Add taste entry"):
        entry = {
            "dog_id": st.session_state.active_dog_id,
            "Dog Name": title_name,
            "Breed": breed,
            "Age (y)": round(age_years, 2),
            "Weight (kg)": round(weight_kg, 2),
            "Protein": None if log_meat == "(skip)" else log_meat,
            "Veg": None if log_veg == "(skip)" else log_veg,
            "Preference": love_level,
            "Notes": notes.strip(),
        }
        st.session_state.taste_log.append(entry)
        st.success("Entry added to this dog's session log.")

    dog_entries = [e for e in st.session_state.taste_log if e.get("dog_id") == st.session_state.active_dog_id]

    if dog_entries:
        log_df = pd.DataFrame(dog_entries)

        st.markdown("### This dog's taste log")
        st.dataframe(log_df, use_container_width=True, height=260)

        st.markdown("### Preference summary")

        def pref_score(p: str) -> int:
            return {"Dislike": 0, "Neutral": 1, "Like": 2, "Love": 3}.get(p, 1)

        protein_records = log_df.dropna(subset=["Protein"]).copy()
        veg_records = log_df.dropna(subset=["Veg"]).copy()

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if not protein_records.empty:
                protein_records["Score"] = protein_records["Preference"].map(pref_score)
                rank = protein_records.groupby("Protein")["Score"].mean().sort_values(ascending=False).reset_index()
                rank.columns = ["Protein", "Avg Preference Score"]
                bar = (
                    alt.Chart(rank)
                    .mark_bar()
                    .encode(
                        x=alt.X("Avg Preference Score:Q", scale=alt.Scale(domain=[0, 3])),
                        y=alt.Y("Protein:N", sort="-x"),
                        tooltip=["Protein", alt.Tooltip("Avg Preference Score:Q", format=".2f")]
                    )
                    .properties(height=240, title="Protein preference (this dog)")
                )
                st.altair_chart(bar, use_container_width=True)
            else:
                st.caption("No protein preference entries yet.")

        with col_s2:
            if not veg_records.empty:
                veg_records["Score"] = veg_records["Preference"].map(pref_score)
                rank = veg_records.groupby("Veg")["Score"].mean().sort_values(ascending=False).reset_index()
                rank.columns = ["Vegetable", "Avg Preference Score"]
                bar = (
                    alt.Chart(rank)
                    .mark_bar()
                    .encode(
                        x=alt.X("Avg Preference Score:Q", scale=alt.Scale(domain=[0, 3])),
                        y=alt.Y("Vegetable:N", sort="-x"),
                        tooltip=["Vegetable", alt.Tooltip("Avg Preference Score:Q", format=".2f")]
                    )
                    .properties(height=240, title="Vegetable preference (this dog)")
                )
                st.altair_chart(bar, use_container_width=True)
            else:
                st.caption("No vegetable preference entries yet.")

    else:
        st.info("This dog's taste log is empty. Add entries to unlock preference-learning.")


# =========================
# Footer
# =========================

st.markdown("---")
st.caption(
    "Nebula Paw Kitchen™ is an educational planner for cooked fresh feeding. "
    "For long-term complete nutrition—especially for puppies or medical cases—"
    "consult a veterinarian or a board-certified veterinary nutritionist."
)
