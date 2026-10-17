"""Curated "go deeper" sub-interests per taxonomy topic (no LLM, no network)."""

SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "world": ("United Nations", "Ukraine", "China", "Global diplomacy", "Refugees"),
    "pakistan": ("Politics", "Karachi", "Lahore", "Islamabad", "Economy and IMF"),
    "south-asia": ("India", "Afghanistan", "Bangladesh", "Sri Lanka", "Kashmir"),
    "middle-east": ("Gaza", "Iran", "Saudi Arabia", "UAE", "Turkey"),
    "us-politics": ("White House", "Congress", "Supreme Court", "Elections", "Trade policy"),
    "europe": ("UK politics", "European Union", "Germany", "France", "Brexit"),
    "business": ("Earnings", "Mergers and acquisitions", "Retail", "Supply chains", "Banking"),
    "markets": ("Stocks", "Bonds", "Currencies", "Commodities", "PSX"),
    "economy": ("Inflation", "Interest rates", "Jobs", "Trade", "Pakistan economy"),
    "startups": ("Funding rounds", "Y Combinator", "Founders", "Unicorns", "Pakistani startups"),
    "crypto": ("Bitcoin", "Ethereum", "Regulation", "Stablecoins", "DeFi"),
    "personal-finance": ("Saving", "Taxes", "Property", "Retirement", "Investing basics"),
    "tech": ("Apple", "Google", "Microsoft", "Social media", "Big tech regulation"),
    "ai": ("AI agents", "Large language models", "AI policy", "OpenAI", "Anthropic", "Robotics"),
    "software": ("Open source", "Python", "TypeScript", "Developer tools", "Cloud and DevOps"),
    "cybersecurity": ("Data breaches", "Ransomware", "Privacy", "Zero-days", "Surveillance"),
    "gadgets": ("iPhone", "Android phones", "Laptops", "Wearables", "Smart home"),
    "science": ("Physics", "Biology", "Chemistry", "Archaeology", "Neuroscience"),
    "space": ("NASA", "SpaceX", "Mars", "Astronomy", "Moon missions"),
    "health": ("Nutrition", "Mental health", "Cancer research", "Public health", "Fitness"),
    "climate": ("Climate policy", "Extreme weather", "Wildlife", "Oceans", "Pollution"),
    "energy": ("Solar", "Oil and gas", "Electric vehicles", "Nuclear", "Power grids"),
    "food": ("Recipes", "Restaurants", "Street food", "Baking", "Food science"),
    "travel": ("Airlines", "City guides", "Hiking", "Visas", "Budget travel"),
    "education": ("Universities", "Scholarships", "Online learning", "Exams", "EdTech"),
    "careers": ("Remote work", "Job market", "Freelancing", "Management", "Productivity"),
    "cricket": ("PSL", "Pakistan team", "Test cricket", "IPL", "T20 World Cup", "Women's cricket"),
    "football": ("Premier League", "Champions League", "La Liga", "World Cup", "Transfers"),
    "f1": ("Race results", "Drivers", "Ferrari", "Red Bull", "Technical analysis"),
    "sports": ("Tennis", "Basketball", "Olympics", "Hockey", "Boxing and MMA"),
    "film-tv": ("Streaming", "Hollywood", "Netflix", "Documentaries", "Pakistani dramas"),
    "music": ("New albums", "Concerts", "Hip-hop", "Pakistani music", "Music industry"),
    "books": ("Fiction", "Non-fiction", "Book prizes", "Authors", "Poetry"),
    "design": ("Architecture", "Product design", "Typography", "Interiors", "UX"),
    "gaming": ("PlayStation", "Nintendo", "PC gaming", "Esports", "Indie games"),
}


def suggestions_for(topic: str) -> list[str] | None:
    """Sub-interests for a topic slug, or None when the slug is not in the taxonomy."""
    found = SUGGESTIONS.get(topic)
    return list(found) if found is not None else None
