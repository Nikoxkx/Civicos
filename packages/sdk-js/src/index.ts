/**
 * CivicOS JavaScript/TypeScript SDK
 *
 * @example
 * ```typescript
 * import { CivicOS } from "civicos-sdk";
 *
 * const client = new CivicOS({ baseUrl: "http://localhost:8000" });
 * const programs = await client.programs.list({ city: "boston", category: "housing" });
 * ```
 */

export interface CivicOSConfig {
  baseUrl?: string;
  timeout?: number;
}

export interface PaginationMeta {
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ProgramSummary {
  id: string;
  city_id: string;
  category_id: number;
  name: string;
  description: string | null;
  benefit_amount: string | null;
  status: string;
  is_ongoing: boolean;
  languages: string[] | null;
  deadline: string | null;
  created_at: string;
}

export interface ProgramDetail extends ProgramSummary {
  eligibility: string | null;
  eligibility_json: Record<string, unknown> | null;
  how_to_apply: string | null;
  application_url: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  source_url: string;
  source_type: string;
  extracted_at: string | null;
  last_checked_at: string | null;
  updated_at: string;
  category: { id: number; slug: string; name: string; icon: string | null } | null;
}

export interface ProgramListResponse {
  data: ProgramSummary[];
  meta: PaginationMeta;
}

export interface City {
  id: string;
  slug: string;
  name: string;
  state: string;
  timezone: string;
  created_at: string;
}

export interface CityListResponse {
  data: City[];
  meta: PaginationMeta;
}

export interface Category {
  id: number;
  slug: string;
  name: string;
  icon: string | null;
}

export interface ProgramVersion {
  id: string;
  program_id: string;
  snapshot: Record<string, unknown>;
  diff: Record<string, unknown> | null;
  changed_at: string;
}

export interface ProgramHistoryResponse {
  data: ProgramVersion[];
}

export interface ProgramListParams {
  city?: string;
  category?: string;
  language?: string;
  status?: string;
  page?: number;
  limit?: number;
}

export interface SearchParams {
  q: string;
  page?: number;
  limit?: number;
}

class CivicOSError extends Error {
  status: number;
  code: string;

  constructor(status: number, body: Record<string, unknown>) {
    const detail = body.detail as Record<string, unknown> | undefined;
    const error = detail?.error as Record<string, string> | undefined;
    super(error?.message ?? `HTTP ${status}`);
    this.name = "CivicOSError";
    this.status = status;
    this.code = error?.code ?? "UNKNOWN";
  }
}

async function request<T>(baseUrl: string, path: string, params?: Record<string, string | number | undefined>, timeout = 30000): Promise<T> {
  const url = new URL(path, baseUrl);

  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url.toString(), {
      signal: controller.signal,
      headers: { "Accept": "application/json" },
    });

    const body = await response.json() as Record<string, unknown>;

    if (!response.ok) {
      throw new CivicOSError(response.status, body);
    }

    return body as T;
  } finally {
    clearTimeout(timer);
  }
}

export class CivicOS {
  private baseUrl: string;
  private timeout: number;

  programs: ProgramsClient;
  cities: CitiesClient;
  categories: CategoriesClient;
  search: SearchClient;

  constructor(config: CivicOSConfig = {}) {
    this.baseUrl = (config.baseUrl ?? "http://localhost:8000").replace(/\/+$/, "");
    this.timeout = config.timeout ?? 30000;

    this.programs = new ProgramsClient(this.baseUrl, this.timeout);
    this.cities = new CitiesClient(this.baseUrl, this.timeout);
    this.categories = new CategoriesClient(this.baseUrl, this.timeout);
    this.search = new SearchClient(this.baseUrl, this.timeout);
  }
}

class ProgramsClient {
  constructor(private baseUrl: string, private timeout: number) {}

  async list(params: ProgramListParams = {}): Promise<ProgramListResponse> {
    return request<ProgramListResponse>(this.baseUrl, "/v1/programs", params as Record<string, string | number | undefined>, this.timeout);
  }

  async get(programId: string): Promise<ProgramDetail> {
    return request<ProgramDetail>(this.baseUrl, `/v1/programs/${programId}`, undefined, this.timeout);
  }

  async history(programId: string): Promise<ProgramHistoryResponse> {
    return request<ProgramHistoryResponse>(this.baseUrl, `/v1/programs/${programId}/history`, undefined, this.timeout);
  }
}

class CitiesClient {
  constructor(private baseUrl: string, private timeout: number) {}

  async list(page = 1, limit = 50): Promise<CityListResponse> {
    return request<CityListResponse>(this.baseUrl, "/v1/cities", { page, limit }, this.timeout);
  }

  async get(slug: string): Promise<City> {
    return request<City>(this.baseUrl, `/v1/cities/${slug}`, undefined, this.timeout);
  }

  async programs(slug: string, params: Omit<ProgramListParams, "city"> = {}): Promise<ProgramListResponse> {
    return request<ProgramListResponse>(this.baseUrl, `/v1/cities/${slug}/programs`, params as Record<string, string | number | undefined>, this.timeout);
  }
}

class CategoriesClient {
  constructor(private baseUrl: string, private timeout: number) {}

  async list(): Promise<Category[]> {
    return request<Category[]>(this.baseUrl, "/v1/categories", undefined, this.timeout);
  }
}

class SearchClient {
  constructor(private baseUrl: string, private timeout: number) {}

  async search(params: SearchParams): Promise<ProgramListResponse> {
    return request<ProgramListResponse>(this.baseUrl, "/v1/search", params as Record<string, string | number | undefined>, this.timeout);
  }
}
