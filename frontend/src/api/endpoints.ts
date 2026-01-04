import { api, unwrap } from "./client";
import type {
  Asset,
  AssetCreate,
  ExposureCreate,
  ExposureLog,
  EventCreate,
  EventFailureDetail,
  EventFailureDetailCreate,
  EventItem,
  FailureMode,
  FailureModeCreate,
  Part,
  PartCreate,
  PartInstall,
  PartInstallCreate,
  Health,
} from "./types";

// Assets
export const listAssets = (params?: { offset?: number; limit?: number }) => unwrap<Asset[]>(api.get("/assets/", { params }));
export const createAsset = (payload: AssetCreate) => unwrap<Asset>(api.post("/assets/", payload));
export const updateAsset = (id: number, payload: Partial<AssetCreate>) => unwrap<Asset>(api.patch(`/assets/${id}`, payload));
export const deleteAsset = (id: number) => api.delete(`/assets/${id}`);

// Exposures
export const listExposures = (params?: { asset_id?: number; offset?: number; limit?: number }) => unwrap<ExposureLog[]>(api.get("/exposures/", { params }));
export const createExposure = (payload: ExposureCreate) => unwrap<ExposureLog>(api.post("/exposures/", payload));
export const updateExposure = (id: number, payload: Partial<ExposureCreate>) => unwrap<ExposureLog>(api.patch(`/exposures/${id}`, payload));
export const deleteExposure = (id: number) => api.delete(`/exposures/${id}`);

// Events
export const listEvents = (params?: { asset_id?: number; offset?: number; limit?: number }) => unwrap<EventItem[]>(api.get("/events/", { params }));
export const createEvent = (payload: EventCreate) => unwrap<EventItem>(api.post("/events/", payload));
export const updateEvent = (id: number, payload: Partial<EventCreate>) => unwrap<EventItem>(api.patch(`/events/${id}`, payload));
export const deleteEvent = (id: number) => api.delete(`/events/${id}`);

// Failure modes
export const listFailureModes = (params?: { offset?: number; limit?: number }) => unwrap<FailureMode[]>(api.get("/failure-modes/", { params }));
export const createFailureMode = (payload: FailureModeCreate) => unwrap<FailureMode>(api.post("/failure-modes/", payload));
export const updateFailureMode = (id: number, payload: Partial<FailureModeCreate>) => unwrap<FailureMode>(api.patch(`/failure-modes/${id}`, payload));
export const deleteFailureMode = (id: number) => api.delete(`/failure-modes/${id}`);

// Event failure details
export const listEventDetails = (params?: { event_id?: number; offset?: number; limit?: number }) => unwrap<EventFailureDetail[]>(api.get("/event-details/", { params }));
export const createEventDetail = (payload: EventFailureDetailCreate) => unwrap<EventFailureDetail>(api.post("/event-details/", payload));
export const updateEventDetail = (id: number, payload: Partial<EventFailureDetailCreate>) => unwrap<EventFailureDetail>(api.patch(`/event-details/${id}`, payload));
export const deleteEventDetail = (id: number) => api.delete(`/event-details/${id}`);

// Parts and installs
export const listParts = (params?: { offset?: number; limit?: number }) => unwrap<Part[]>(api.get("/parts/", { params }));
export const createPart = (payload: PartCreate) => unwrap<Part>(api.post("/parts/", payload));
export const updatePart = (id: number, payload: Partial<PartCreate>) => unwrap<Part>(api.patch(`/parts/${id}`, payload));
export const deletePart = (id: number) => api.delete(`/parts/${id}`);

export const listPartInstalls = (partId: number) => unwrap<PartInstall[]>(api.get(`/parts/${partId}/installs`));
export const createPartInstall = (partId: number, payload: PartInstallCreate) => unwrap<PartInstall>(api.post(`/parts/${partId}/installs`, payload));
export const updatePartInstall = (installId: number, payload: Partial<PartInstallCreate>) => unwrap<PartInstall>(api.patch(`/parts/installs/${installId}`, payload));
export const deletePartInstall = (installId: number) => api.delete(`/parts/installs/${installId}`);

// Health
export const getHealth = () => unwrap<Health>(api.get("/health"));
