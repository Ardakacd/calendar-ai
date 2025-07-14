export interface Event {
  id: string;
  title: string;
  startDate: string;
  endDate: string;
  duration?: number;
  location?: string;
  user_id?: number;
}

export interface EventCreate {
  title: string;
  startDate: string;
  duration?: number;
  location?: string;
}
