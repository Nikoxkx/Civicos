# CivicOS JavaScript SDK

```bash
npm install civicos-sdk
```

```typescript
import { CivicOS } from "civicos-sdk";

const client = new CivicOS({ baseUrl: "http://localhost:8000" });

// List housing programs in Boston
const programs = await client.programs.list({ city: "boston", category: "housing" });
programs.data.forEach(p => console.log(p.name));

// Get full program details
const detail = await client.programs.get("abc-123");

// Full-text search
const results = await client.search.search({ q: "rental assistance" });

// List available cities
const cities = await client.cities.list();
```
