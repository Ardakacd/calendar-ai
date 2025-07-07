export interface Event {
  id: string;
  title: string;
  startDate: string;
  endDate?: string;
  duration?: number;
  location?: string;
}

export interface EventConfirmationData {
    title: string;
    startDate: string;
    duration?: number;
    location?: string;
    event_id?: string;
  }