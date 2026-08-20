/**
 * licensing.ts
 *
 * API client for the Business License Tracking feature.
 * Mirrors the conventions of your existing dms.ts - adjust BASE_URL /
 * fetch wrapper / auth header injection to match your actual dms.ts
 * implementation (e.g. if you use a shared `apiFetch` helper with
 * credentials/cookies or a bearer token, swap the calls below to use it).
 */

const BASE_URL = "/api/licensing";

// ---------- Types ----------

export type MunicipalityType =
  | "City"
  | "District Municipality"
  | "Town"
  | "Village"
  | "Island Municipality"
  | "Mountain Resort Municipality"
  | "Resort Municipality"
  | "Indian Government District"
  | "Other";

export type LicenseScope = "Municipal" | "Intermunicipal";

export type LicenseStatus =
  | "Active"
  | "Expiring Soon"
  | "Expired"
  | "Inactive"
  | "Pending";

export interface Province {
  id: string;
  code: string;
  name: string;
  enabled: boolean;
}

export interface RegionalDistrict {
  id: string;
  province_id: string;
  name: string;
  enabled: boolean;
}

export interface Municipality {
  id: string;
  name: string;
  municipality_type: MunicipalityType;
  regional_district_id: string;
  tracking_enabled: boolean;
  notes?: string | null;
}

export interface License {
  id: string;
  scope: LicenseScope;
  municipality_id?: string | null;
  regional_district_id?: string | null;
  license_number?: string | null;
  issuing_authority?: string | null;
  issue_date?: string | null;
  expiry_date: string;
  cost?: number | null;
  status_override?: LicenseStatus | null;
  warning_threshold_days?: number | null;
  document_reference?: string | null;
  notes?: string | null;
  computed_status: LicenseStatus;
  days_until_expiry: number;
}

export interface GovernmentLicenseRow {
  province_name: string;
  region_name: string;
  municipality_id: string;
  municipality_name: string;
  municipality_type: MunicipalityType;
  tracking_enabled: boolean;
  license_id?: string | null;
  license_scope?: LicenseScope | null;
  license_number?: string | null;
  status_override?: LicenseStatus | null;
  expiry_date?: string | null;
  computed_status?: LicenseStatus | null;
  days_until_expiry?: number | null;
  cost?: number | null;
  covered_via_region: boolean;
  company_ids: string[];
  imbl_region_ids: string[];
  imbl_region_names: string[];
  issuing_municipality_id?: string | null;
  issuing_municipality_name?: string | null;
  imbl_region_id?: string | null;
  imbl_region_name?: string | null;
}

export type DashboardStatusFilter = "active" | "inactive" | "all";

export interface Company {
  id: string;
  name: string;
  short_name: string;
  enabled: boolean;
}

export function getCompanies(): Promise<Company[]> {
  return request("/companies");
}

export function addCompanyToLicense(licenseId: string, companyId: string): Promise<void> {
  return request(`/licenses/${licenseId}/companies/${companyId}`, { method: "POST" });
}

export function removeCompanyFromLicense(licenseId: string, companyId: string): Promise<void> {
  return request(`/licenses/${licenseId}/companies/${companyId}`, { method: "DELETE" });
}

// ---------- Fetch helper ----------
// NOTE: swap this for your existing fetch wrapper (e.g. one that injects
// auth headers / cookies / handles 401s) if dms.ts already has one.
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Licensing API error ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

// ---------- Provinces ----------

export function getProvinces(): Promise<Province[]> {
  return request("/provinces");
}

// ---------- Regional Districts ----------

export function getRegionalDistricts(provinceId?: string): Promise<RegionalDistrict[]> {
  const qs = provinceId ? `?province_id=${encodeURIComponent(provinceId)}` : "";
  return request(`/regional-districts${qs}`);
}

// ---------- Municipalities ----------

export interface ListMunicipalitiesParams {
  regionalDistrictId?: string;
  search?: string;
  trackingEnabled?: boolean;
}

export function getMunicipalities(params: ListMunicipalitiesParams = {}): Promise<Municipality[]> {
  const qs = new URLSearchParams();
  if (params.regionalDistrictId) qs.set("regional_district_id", params.regionalDistrictId);
  if (params.search) qs.set("search", params.search);
  if (params.trackingEnabled !== undefined) qs.set("tracking_enabled", String(params.trackingEnabled));
  const qsStr = qs.toString();
  return request(`/municipalities${qsStr ? `?${qsStr}` : ""}`);
}

export function createMunicipality(payload: {
  name: string;
  municipality_type: MunicipalityType;
  regional_district_id: string;
  tracking_enabled?: boolean;
  notes?: string;
}): Promise<Municipality> {
  return request("/municipalities", { method: "POST", body: JSON.stringify(payload) });
}

export function updateMunicipality(
  id: string,
  payload: Partial<Pick<Municipality, "name" | "municipality_type" | "regional_district_id" | "tracking_enabled" | "notes">>
): Promise<Municipality> {
  return request(`/municipalities/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteMunicipality(id: string): Promise<void> {
  return request(`/municipalities/${id}`, { method: "DELETE" });
}

export function bulkToggleTracking(payload: {
  province_id?: string;
  regional_district_id?: string;
  tracking_enabled: boolean;
}): Promise<{ updated_count: number }> {
  return request("/municipalities/bulk-toggle", { method: "POST", body: JSON.stringify(payload) });
}

// ---------- IMBL ----------
export interface ImblRegionMember {
  id: string;
  name: string;
  municipality_type: MunicipalityType;
  regional_district_id: string;
}

export interface ImblRegion {
  id: string;
  name: string;
  enabled: boolean;
  municipalities: ImblRegionMember[];
}

export function getImblRegions(): Promise<ImblRegion[]> {
  return request("/imbl-regions");
}

export function createImblRegion(name: string): Promise<ImblRegion> {
  return request("/imbl-regions", { method: "POST", body: JSON.stringify({ name }) });
}

export function updateImblRegion(id: string, payload: { name?: string; enabled?: boolean }): Promise<ImblRegion> {
  return request(`/imbl-regions/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteImblRegion(id: string): Promise<void> {
  return request(`/imbl-regions/${id}`, { method: "DELETE" });
}

export function addMunicipalityToImblRegion(imblRegionId: string, municipalityId: string): Promise<void> {
  return request(`/imbl-regions/${imblRegionId}/municipalities/${municipalityId}`, { method: "POST" });
}

export function removeMunicipalityFromImblRegion(imblRegionId: string, municipalityId: string): Promise<void> {
  return request(`/imbl-regions/${imblRegionId}/municipalities/${municipalityId}`, { method: "DELETE" });
}

// ---------- Licenses ----------

export interface ListLicensesParams {
  municipalityId?: string;
  regionalDistrictId?: string;
}

export function getLicenses(params: ListLicensesParams = {}): Promise<License[]> {
  const qs = new URLSearchParams();
  if (params.municipalityId) qs.set("municipality_id", params.municipalityId);
  if (params.regionalDistrictId) qs.set("regional_district_id", params.regionalDistrictId);
  const qsStr = qs.toString();
  return request(`/licenses${qsStr ? `?${qsStr}` : ""}`);
}

export interface CreateLicensePayload {
  scope: LicenseScope;
  municipality_id?: string;
  regional_district_id?: string;
  license_number?: string;
  issuing_authority?: string;
  issue_date?: string;
  expiry_date: string;
  cost?: number;
  status_override?: LicenseStatus;
  warning_threshold_days?: number;
  document_reference?: string;
  notes?: string;
  issuing_municipality_id?: string;
  imbl_region_id?: string;
}

export function createLicense(payload: CreateLicensePayload): Promise<License> {
  return request("/licenses", { method: "POST", body: JSON.stringify(payload) });
}

export function updateLicense(
  id: string,
  payload: Partial<Omit<CreateLicensePayload, "scope" | "municipality_id" | "regional_district_id">>
): Promise<License> {
  return request(`/licenses/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function deleteLicense(id: string): Promise<void> {
  return request(`/licenses/${id}`, { method: "DELETE" });
}

// ---------- Dashboard ----------

export interface DashboardParams {
  statusFilter?: DashboardStatusFilter;
  provinceId?: string;
  regionalDistrictId?: string;
  search?: string;
  trackingEnabledOnly?: boolean;
  companyId?: string;
}

export function getDashboard(params: DashboardParams = {}): Promise<GovernmentLicenseRow[]> {
  const qs = new URLSearchParams();
  if (params.statusFilter) qs.set("status_filter", params.statusFilter);
  if (params.provinceId) qs.set("province_id", params.provinceId);
  if (params.regionalDistrictId) qs.set("regional_district_id", params.regionalDistrictId);
  if (params.search) qs.set("search", params.search);
  if (params.companyId) qs.set("company_id", params.companyId);
  if (params.trackingEnabledOnly !== undefined) {
    qs.set("tracking_enabled_only", String(params.trackingEnabledOnly));
  }
  const qsStr = qs.toString();
  return request(`/dashboard${qsStr ? `?${qsStr}` : ""}`);
}

export function getExpiringSoon(withinDays = 30): Promise<GovernmentLicenseRow[]> {
  return request(`/expiring-soon?within_days=${withinDays}`);
}