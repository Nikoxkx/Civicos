# CivicOS Python SDK

```bash
pip install civicos
```

```python
import civicos

client = civicos.Client(base_url="http://localhost:8000")

# List housing programs in Boston
programs = client.programs.list(city="boston", category="housing")
for p in programs["data"]:
    print(p["name"])

# Get full program details
detail = client.programs.get("abc-123")

# Full-text search
results = client.search.search("rental assistance")

# List available cities and categories
cities = client.cities.list()
categories = client.categories.list()
```
