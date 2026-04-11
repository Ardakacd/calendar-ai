export type EventCategory = 'work' | 'personal' | 'health' | 'social';

export interface Event {
  id: string;
  title: string;
  category?: EventCategory;
  description?: string;
  startDate: string;
  endDate: string;
  duration?: number;
  location?: string;
  user_id?: number;
  recurrence_id?: string;
  recurrence_type?: string;
  rrule_string?: string;
}

export interface EventCreate {
  title: string;
  category?: EventCategory;
  description?: string;
  startDate: string;
  duration?: number;
  location?: string;
}

export interface SeriesUpdateRequest {
  scope: 'all' | 'future';
  from_date?: string;        // ISO 8601 — required when scope='future'
  title?: string;
  category?: EventCategory;
  description?: string;
  location?: string;
  duration?: number;
  time_shift_minutes?: number;
}

export interface SeriesUpdateResponse {
  updated_count: number;
  recurrence_id: string;
  scope: string;
  message: string;
}

export interface SeriesDeleteResponse {
  deleted_count: number;
  recurrence_id: string;
  scope: string;
  message: string;
}
