#!/usr/bin/env python3
"""
Smart Travel Assistant - Full Hackathon MVP
Features:
- Optional language auto-detect (langdetect if installed)
- Fuzzy phrase matching and translation adapter
- Language-aware provider scoring and availability scheduling
- Booking persistence (data/bookings.json)
- Ratings & reviews, provider locations with map links
- Mock SMS/WhatsApp notification adapter
- Mini analytics dashboard
- Polished console UX
"""

import json
import os
import uuid
import string
import webbrowser
from datetime import datetime, timedelta
from difflib import get_close_matches
from collections import Counter

# Optional language detection
try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False

DATA_DIR = "data"
BOOKINGS_FILE = os.path.join(DATA_DIR, "bookings.json")
PROVIDERS_FILE = os.path.join(DATA_DIR, "providers.json")

# Demo provider data (includes location and availability)
default_providers = [
    {"id": "p1", "name": "Ravi", "service": "Taxi Driver", "language": "Telugu", "rating": 4.8,
     "reviews": [], "available": True, "next_available": None, "location": {"lat": 17.45, "lng": 78.45}},
    {"id": "p2", "name": "Maria", "service": "Tour Guide", "language": "French", "rating": 4.9,
     "reviews": [], "available": True, "next_available": None, "location": {"lat": 48.85, "lng": 2.35}},
    {"id": "p3", "name": "Carlos", "service": "City Tour", "language": "Spanish", "rating": 4.7,
     "reviews": [], "available": True, "next_available": None, "location": {"lat": 19.43, "lng": -99.13}},
]

# Phrasebook for demo translations
phrasebook = {
    "hello": {"French": "Bonjour", "Spanish": "Hola", "Telugu": "Namaskaram"},
    "thank you": {"French": "Merci", "Spanish": "Gracias", "Telugu": "Dhanyavadalu"},
    "how much": {"French": "Combien", "Spanish": "Cuánto", "Telugu": "Enta"},
    "where is": {"French": "Où est", "Spanish": "Dónde está", "Telugu": "Ekkada undi"},
    "i need a taxi": {"French": "J'ai besoin d'un taxi", "Spanish": "Necesito un taxi", "Telugu": "Naku taxi kavali"},
}

# Utilities
def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_json(path, default):
    ensure_data_dir()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    ensure_data_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Load or initialize data
providers = load_json(PROVIDERS_FILE, default_providers)
bookings = load_json(BOOKINGS_FILE, [])

# Text normalization and fuzzy helpers
def normalize_text(s):
    s = (s or "").strip().lower()
    s = s.translate(str.maketrans("", "", string.punctuation))
    return " ".join(s.split())

def fuzzy_match_phrase(phrase):
    keys = list(phrasebook.keys())
    phrase_norm = normalize_text(phrase)
    close = get_close_matches(phrase_norm, keys, n=1, cutoff=0.6)
    return close[0] if close else None

# Language detection adapter
def detect_language(text):
    text = (text or "").strip()
    if not text:
        return None
    if LANGDETECT_AVAILABLE:
        try:
            code = detect(text)
            mapping = {'fr': 'French', 'es': 'Spanish', 'te': 'Telugu', 'en': 'English'}
            return mapping.get(code, None)
        except Exception:
            return None
    # Heuristic fallback
    t = text.lower()
    if any(w in t for w in ["bonjour", "merci", "où", "combien"]):
        return "French"
    if any(w in t for w in ["hola", "gracias", "dónde", "cuánto"]):
        return "Spanish"
    if any(w in t for w in ["namaskaram", "dhanyavadalu", "enta", "ekkada"]):
        return "Telugu"
    return None

# Translation adapter (keeps signature for easy swap to API)
def translate_phrase(phrase, target_lang):
    key = fuzzy_match_phrase(phrase)
    if not key:
        return None, None
    translations = phrasebook.get(key, {})
    lang = (target_lang or "").strip().title()
    if lang in translations:
        return translations[lang], key
    return None, key

# Provider matching and scoring
def match_providers(preferred_language=None, service_filter=None, only_available=True):
    lang = (preferred_language or "").strip().title() if preferred_language else None
    candidates = [p for p in providers if (service_filter is None or service_filter.lower() in p["service"].lower())]
    if only_available:
        candidates = [p for p in candidates if p.get("available", True)]
    scored = []
    for p in candidates:
        score = p.get("rating", 0)
        if lang and p.get("language", "").strip().title() == lang:
            score += 100
        # small recency boost if recently reviewed
        if p.get("reviews"):
            score += min(len(p["reviews"]) * 0.1, 1.0)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]

# Booking and persistence
def create_booking(tourist, provider, language=None, phone=None):
    booking = {
        "id": str(uuid.uuid4())[:8],
        "tourist": tourist,
        "provider_id": provider["id"],
        "provider_name": provider["name"],
        "service": provider["service"],
        "language": language or provider.get("language"),
        "phone": phone,
        "status": "Confirmed",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "history": [{"ts": datetime.utcnow().isoformat() + "Z", "status": "Confirmed"}]
    }
    bookings.append(booking)
    save_json(BOOKINGS_FILE, bookings)
    return booking

def update_provider_availability(provider_id, available, next_available=None):
    for p in providers:
        if p["id"] == provider_id:
            p["available"] = available
            p["next_available"] = next_available
            save_json(PROVIDERS_FILE, providers)
            return True
    return False

# Reviews
def add_review(provider_id, rating, comment=""):
    for p in providers:
        if p["id"] == provider_id:
            p.setdefault("reviews", []).append({"rating": rating, "comment": comment, "ts": datetime.utcnow().isoformat()})
            ratings = [r["rating"] for r in p["reviews"]]
            p["rating"] = round(sum(ratings) / len(ratings), 2)
            save_json(PROVIDERS_FILE, providers)
            return p["rating"]
    return None

# Mock notification adapter
def notify_user_mock(phone, message):
    print(f"\n[NOTIFICATION MOCK] To: {phone or 'unknown'} | Message: {message}")

# Map link helper
def open_provider_map(provider):
    loc = provider.get("location")
    if not loc:
        print("No location available for this provider.")
        return
    url = f"https://www.google.com/maps/search/?api=1&query={loc['lat']},{loc['lng']}"
    print("Opening map:", url)
    try:
        webbrowser.open(url)
    except Exception:
        pass

# Analytics
def analytics_summary():
    if not bookings:
        print("\nNo bookings yet — analytics will appear after bookings.")
        return
    langs = Counter(b.get('language', 'Unknown') for b in bookings)
    services = Counter(b['service'] for b in bookings)
    top_providers = Counter(b['provider_name'] for b in bookings)
    print("\n=== Analytics Summary ===")
    print("Bookings by language:", dict(langs))
    print("Top services:", services.most_common(3))
    print("Top providers:", top_providers.most_common(3))
    avg_rating = round(sum(p.get("rating", 0) for p in providers) / len(providers), 2)
    print("Average provider rating:", avg_rating)

# Console UI flows
def show_providers(listing=None):
    lst = listing if listing is not None else providers
    print("\nAvailable Local Service Providers")
    for i, p in enumerate(lst, start=1):
        avail = "Available" if p.get("available", True) else f"Busy until {p.get('next_available')}"
        print(f"{i}. {p['name']} - {p['service']} [{p['language']}] ⭐{p.get('rating','N/A')} | {avail}")

def translate_message_flow():
    phrase = input("Enter message (e.g., hello / thank you / how much / where is): ").strip()
    if not phrase:
        print("No input provided.")
        return
    detected = detect_language(phrase)
    if detected:
        print(f"Detected language: {detected}")
    target = input("Translate to (French / Spanish / Telugu) or press Enter to use detected language: ").strip()
    if not target and detected:
        target = detected
    translated, matched_key = translate_phrase(phrase, target)
    if translated:
        print(f"\nTranslated ({matched_key} → {target.strip().title()}): {translated}")
    elif matched_key:
        print(f"\nNo translation for '{matched_key}' in {target.strip().title()}.")
    else:
        # suggest close phrases
        keys = list(phrasebook.keys())
        close = get_close_matches(normalize_text(phrase), keys, n=3, cutoff=0.4)
        if close:
            print("\nCould not find an exact phrase. Did you mean:", ", ".join(close))
        else:
            print("\nTranslation not available in demo version.")

def book_service_flow():
    name = input("Enter your name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
    phone = input("Phone (optional, for mock notification): ").strip() or None
    pref_lang = input("Preferred language (optional): ").strip().title() or None
    service_want = input("What service do you want (taxi / tour / city) or leave blank for any: ").strip().lower() or None
    matched = match_providers(pref_lang, service_filter=service_want, only_available=True)
    if not matched:
        print("No immediate providers match your preferences. Showing all providers (including busy).")
        matched = match_providers(pref_lang, service_filter=service_want, only_available=False)
    show_providers(matched)
    choice = input("Select provider number to book (or 'c' to cancel): ").strip()
    if choice.lower() == 'c':
        print("Booking cancelled.")
        return
    if not choice.isdigit():
        print("Invalid input. Please enter a number.")
        return
    idx = int(choice) - 1
    if 0 <= idx < len(matched):
        provider = matched[idx]
        # If provider busy, offer next available scheduling
        if not provider.get("available", True):
            print(f"Provider is busy until {provider.get('next_available')}.")
            schedule = input("Schedule for next available time? (y/n): ").strip().lower()
            if schedule != 'y':
                print("Booking cancelled.")
                return
            # simulate scheduling by setting next_available to now + 1 hour
            provider["next_available"] = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
            provider["available"] = False
            save_json(PROVIDERS_FILE, providers)
        booking = create_booking(name, provider, language=pref_lang, phone=phone)
        print("\nBooking Confirmed!")
        print(f"Booking ID: {booking['id']}")
        print(f"Tourist: {booking['tourist']}")
        print(f"Provider: {booking['provider_name']}")
        print(f"Service: {booking['service']}")
        print(f"Status: {booking['status']}")
        # Mock notification
        notify_user_mock(phone, f"Booking {booking['id']} confirmed with {provider['name']}")
        # Offer to open map
        open_map = input("Open provider location in maps? (y/n): ").strip().lower()
        if open_map == 'y':
            open_provider_map(provider)
        # Simulate trip completion and ask for rating
        complete = input("Simulate trip completion now and leave a rating? (y/n): ").strip().lower()
        if complete == 'y':
            rating = input("Rate your experience (1-5): ").strip()
            try:
                r = float(rating)
                if 1 <= r <= 5:
                    comment = input("Optional comment: ").strip()
                    new_avg = add_review(provider["id"], r, comment)
                    print(f"Thanks! Updated provider rating: {new_avg}")
                else:
                    print("Rating out of range; skipping.")
            except Exception:
                print("Invalid rating; skipping.")
    else:
        print("Invalid selection.")

def view_bookings_flow():
    if not bookings:
        print("No bookings yet.")
        return
    print("\nAll Bookings")
    for b in bookings:
        print(f"- {b['id']} | {b['tourist']} → {b['provider_name']} | {b['service']} | {b['created_at']} | {b['status']}")

def admin_menu():
    print("\n=== Admin Menu ===")
    print("1. Show analytics")
    print("2. Toggle provider availability")
    print("3. Show providers")
    print("4. Back")
    choice = input("Choose: ").strip()
    if choice == "1":
        analytics_summary()
    elif choice == "2":
        show_providers()
        sel = input("Select provider number to toggle availability: ").strip()
        if not sel.isdigit():
            print("Invalid input.")
            return
        idx = int(sel) - 1
        if 0 <= idx < len(providers):
            p = providers[idx]
            new_avail = not p.get("available", True)
            next_av = None
            if not new_avail:
                next_av = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
            update_provider_availability(p["id"], new_avail, next_av)
            print(f"Provider {p['name']} availability set to {new_avail}.")
        else:
            print("Invalid selection.")
    elif choice == "3":
        show_providers()
    else:
        return

def main():
    try:
        while True:
            print("\n🌍 SMART TRAVEL ASSISTANT — FULL DEMO")
            print("1. Translate Message")
            print("2. View Local Providers")
            print("3. Book a Service")
            print("4. View Bookings")
            print("5. Admin")
            print("6. Exit")
            option = input("Choose option: ").strip()
            if option == "1":
                translate_message_flow()
            elif option == "2":
                show_providers()
            elif option == "3":
                book_service_flow()
            elif option == "4":
                view_bookings_flow()
            elif option == "5":
                admin_menu()
            elif option == "6":
                print("Thank you for using Smart Travel Assistant!")
                break
            else:
                print("Invalid option. Try again.")
    except KeyboardInterrupt:
        print("\nExiting. Goodbye!")

if __name__ == "__main__":
    # Ensure initial data saved so persistence works on first run
    save_json(PROVIDERS_FILE, providers)
    save_json(BOOKINGS_FILE, bookings)
    main()