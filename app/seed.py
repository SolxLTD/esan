from app.models import Product, Training

# INDICATIVE PRICES (Oct 2026): confirm with your suppliers; replace prices, NAFDAC numbers and label directions with your real stock.
P = [
    ("Glyphosate 360SL Herbicide", "Herbicides", 6500, "1L", "Glyphosate", "Pre-plant weed clearing, plantation weeding", "Dilute as per the product label."),
    ("Atrazine 500SC Herbicide", "Herbicides", 7500, "1L", "Atrazine", "Weed control in maize", "Dilute as per the product label."),
    ("2,4-D Amine 720SL Herbicide", "Herbicides", 6000, "1L", "2,4-D amine", "Broadleaf weeds in maize and rice", "Dilute as per the product label."),
    ("Nicosulfuron 40OD Herbicide", "Herbicides", 9500, "1L", "Nicosulfuron", "Post-emergence grass control in maize", "Dilute as per the product label."),
    ("Glufosinate-ammonium 150SL", "Herbicides", 12000, "1L", "Glufosinate-ammonium", "Non-selective weed control in plantations and fallow land", "Dilute as per the product label."),
    ("Cypermethrin Insecticide", "Insecticides", 4500, "1L", "Cypermethrin", "Caterpillars, aphids, beetles on vegetables and cereals", "Dilute as per the product label."),
    ("Lambda-cyhalothrin Insecticide", "Insecticides", 5500, "1L", "Lambda-cyhalothrin", "Broad-spectrum insect control", "Dilute as per the product label."),
    ("Emamectin Benzoate Insecticide", "Insecticides", 6500, "100g", "Emamectin benzoate", "Fall armyworm and caterpillars on maize and vegetables", "Mix as per the product label."),
    ("Imidacloprid 200SL Insecticide", "Insecticides", 8000, "1L", "Imidacloprid", "Sucking pests such as aphids and whiteflies", "Dilute as per the product label."),
    ("Neem Oil (Organic)", "Insecticides", 18000, "1L", "Azadirachtin (neem)", "Organic control of many insect pests", "Dilute as per the product label."),
    ("Mancozeb 80WP Fungicide", "Fungicides", 3800, "1kg", "Mancozeb", "Blight and leaf spot on tomato, pepper, vegetables", "Mix as per the product label."),
    ("Metalaxyl + Mancozeb Fungicide", "Fungicides", 7000, "1kg", "Metalaxyl + Mancozeb", "Downy mildew and late blight in tomato, pepper, vegetables", "Mix as per the product label."),
    ("Copper Hydroxide Fungicide", "Fungicides", 6500, "1kg", "Copper hydroxide", "Bacterial and fungal diseases, including cocoa and vegetables", "Mix as per the product label."),
    ("NPK 15-15-15", "Fertilizers", 55000, "50kg bag", "N-P-K 15-15-15", "Basal fertilizer for most crops", "Apply at the rate on the bag."),
    ("NPK 20-10-10", "Fertilizers", 55000, "50kg bag", "N-P-K 20-10-10", "Vegetative growth in maize, cassava, vegetables", "Apply at the rate on the bag."),
    ("Urea 46%", "Fertilizers", 45000, "50kg bag", "Nitrogen 46%", "Top dressing for maize and vegetables", "Apply at the rate on the bag."),
    ("Muriate of Potash (MOP)", "Fertilizers", 50000, "50kg bag", "Potassium chloride", "Fruiting, tuber bulking and oil palm", "Apply at the rate on the bag."),
    ("Organic Compost", "Fertilizers", 8000, "25kg bag", "", "Soil conditioning and organic farming", "Apply at the rate on the bag."),
    ("16L Knapsack Sprayer", "Sprayers & Safety Gear", 22000, "1 unit", "", "Manual spraying of chemicals", ""),
    ("Applicator Safety Kit", "Sprayers & Safety Gear", 9500, "1 kit", "", "Gloves, mask, goggles, apron", ""),
    ("Nitrile Gloves (Chemical-resistant)", "Sprayers & Safety Gear", 1500, "1 pair", "", "Hand protection when mixing and spraying", ""),
    ("Respirator Mask with Filters", "Sprayers & Safety Gear", 3500, "1 unit", "", "Protection from spray mist and fumes", ""),
]
T = [
    ("Safe Agrochemical Handling & Application", "Reading labels, correct dilution and calibration, PPE, storage, disposal of containers, re-entry and pre-harvest intervals.", "1 day", 10000, "To be announced"),
    ("Weed, Pest & Disease Management for Maize and Vegetables", "Identifying common problems, choosing the right product, timing of application, avoiding resistance.", "2 days", 20000, "To be announced"),
    ("Fertilizer Programs for Higher Yield", "Soil basics, choosing NPK vs straight fertilizers, rates, timing and placement.", "1 day", 12000, "To be announced"),
]


def seed(session):
    for i, (n, c, pr, pk, ai, uf, d) in enumerate(P):
        session.add(Product(name=n, category=c, price=pr, pack=pk, active_ingredient=ai,
                            nafdac_no="Add NAFDAC no.", use_for=uf, directions=d,
                            description=f"{n} in a {pk} pack, for {uf.lower()}. Follow the product label and local guidance.",
                            featured=i % 3 == 0))
    for t, d, du, pr, nd in T:
        session.add(Training(title=t, description=d, duration=du, price=pr, next_date=nd))
    session.commit()
