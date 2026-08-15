export type Site = {
  id: string;
  code: string;
  name: string;
  short_code: string;
  is_active: boolean;
};

export type WarehouseTypeConfig = {
  id: string;
  code: string;
  description: string;
};

export type WarehouseCodeConfig = {
  id: string;
  warehouse_type_code: string;
  code: string;
  description: string;
};

export type LocationTypeConfig = {
  id: string;
  warehouse_type_code: string;
  code: string;
  description: string;
  is_whole_warehouse: boolean;
};

export type CategoryRackMapping = {
  id: string;
  warehouse_type_code: string;
  raw_category_text: string;
  location_type_config_id: string;
};

export type Warehouse = {
  id: string;
  site_id: string;
  warehouse_type_code: string;
  warehouse_code: string;
  duplicate_letter: string | null;
  generated_code: string;
  name: string;
  description: string | null;
  capacity: number | null;
  is_active: boolean;
  created_at: string;
  has_pending_revision: boolean;
  pic_acknowledged_at: string | null;
  pic_acknowledged_by: string | null;
  needs_pic_review: boolean;
};

export type Location = {
  id: string;
  warehouse_id: string;
  location_type_code: string;
  seq: number;
  generated_code: string;
  category_rack_raw: string | null;
  description: string;
  is_active: boolean;
  created_at: string;
  has_pending_revision: boolean;
  layout_x: number | null;
  layout_y: number | null;
  layout_width: number | null;
  layout_height: number | null;
  pic_acknowledged_at: string | null;
  pic_acknowledged_by: string | null;
  needs_pic_review: boolean;
};

export type UserAccount = {
  id: string;
  full_name: string;
  email: string;
  role: "admin" | "pic";
  site_id: string | null;
  is_active: boolean;
};

export type RevisionEntityType = "warehouse" | "location";

export type RawImportBatch = {
  id: string;
  site_id: string;
  file_name: string;
  uploaded_at: string;
};

export type RawRackRow = {
  code_rack: string | null;
  description: string;
  is_active: boolean;
};

export type RawWarehouseSuggestion = {
  id: string;
  batch_id: string;
  legacy_code: string;
  legacy_name: string;
  consolidated_legacy_names: string[];
  raw_rows: RawRackRow[];
  suggested_warehouse_type_code: string | null;
  suggested_warehouse_code: string | null;
  reasoning: string | null;
  status: "pending" | "approved" | "rejected";
  created_warehouse_id: string | null;
  resolved_at: string | null;
};

export type RawLocationSuggestion = {
  id: string;
  batch_id: string;
  warehouse_suggestion_id: string;
  warehouse_id: string;
  legacy_code: string | null;
  legacy_description: string;
  is_active_raw: boolean;
  suggested_category_rack: string | null;
  reasoning: string | null;
  status: "pending" | "approved" | "rejected";
  created_location_id: string | null;
  created_merge_suggestion_id: string | null;
  resolved_at: string | null;
};

export type Revision = {
  id: string;
  entity_type: RevisionEntityType;
  entity_id: string;
  submitted_by: string;
  submitted_at: string;
  original_value: Record<string, string | number | null>;
  proposed_value: Record<string, string | number | null>;
  comment: string;
  status: "pending" | "approved" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  final_value: Record<string, string | number | null> | null;
};

export type UploadBatch = {
  id: string;
  file_type: "warehouse_master" | "location_master";
  file_name: string;
  row_count: number;
  success_count: number;
  error_count: number;
  pending_count: number;
  status: "processing" | "completed" | "failed";
  uploaded_at: string;
};

export type UploadError = {
  row_number: number;
  column_name: string;
  error_message: string;
};

export type MergeSuggestion = {
  id: string;
  upload_batch_id: string | null;
  row_number: number | null;
  warehouse_id: string;
  location_type_code: string;
  raw_category_rack: string | null;
  raw_description: string;
  suggested_location_id: string;
  similarity_score: number;
  reasoning: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  resolved_at: string | null;
};

export type WarehouseSummary = {
  total_warehouses: number;
  active_warehouses: number;
  empty_warehouses: number;
  underutilized_warehouses: number;
  overloaded_warehouses: number;
  warehouses_without_capacity_set: number;
};

export type LocationSummary = {
  total_locations: number;
  pending_duplicate_review: number;
};

export type DashboardSummary = {
  warehouses: WarehouseSummary;
  locations: LocationSummary;
};

export type WarehouseCapacity = {
  location_count: number;
  capacity: number | null;
  occupancy_rate: number | null;
  status: "empty" | "underutilized" | "normal" | "overloaded" | "no_capacity_set";
};

export type Recommendation = {
  id: string;
  category: "merge_opportunity" | "redundant_warehouse" | "underutilized" | "overloaded";
  warehouse_ids: string[];
  title: string;
  explanation: string;
  created_at: string;
};
