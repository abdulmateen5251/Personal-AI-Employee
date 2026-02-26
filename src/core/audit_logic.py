SUBSCRIPTION_PATTERNS = {
    "netflix.com": "Netflix",
    "spotify.com": "Spotify",
    "adobe.com": "Adobe Creative Cloud",
    "notion.so": "Notion",
    "slack.com": "Slack",
}


def analyze_transaction(transaction: dict):
    description = str(transaction.get("description", "")).lower()
    for pattern, name in SUBSCRIPTION_PATTERNS.items():
        if pattern in description:
            return {
                "type": "subscription",
                "name": name,
                "amount": transaction.get("amount"),
                "date": transaction.get("date"),
            }
    return None
