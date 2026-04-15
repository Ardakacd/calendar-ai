/**
 * Date utility functions for consistent date handling across the app
 */

/**
 * Safely parse a date string and return a Date object
 * Handles ISO strings with timezone information properly
 */
export const parseDate = (dateString: string): Date => {
  if (!dateString) {
    throw new Error("Date string is required");
  }

  const date = new Date(dateString);

  if (isNaN(date.getTime())) {
    throw new Error(`Invalid date string: ${dateString}`);
  }

  return date;
};

/**
 * Format a date string for display in the user's local timezone
 */
export const formatDateTime = (dateString: string): string => {
  try {
    const date = parseDate(dateString);
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch (error) {
    console.error("Error formatting date:", error, dateString);
    return "Invalid date";
  }
};

/**
 * Format a date string for display with weekday and short format
 */
export const formatDateWithWeekday = (dateString: string): string => {
  try {
    const date = parseDate(dateString);
    const datePart = date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
    const timePart = date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return `${datePart}, ${timePart}`;
  } catch (error) {
    console.error("Error formatting date with weekday:", error, dateString);
    return "Invalid date";
  }
};

/**
 * Format just the time portion of a date string
 */
export const formatTime = (dateString: string): string => {
  try {
    const date = parseDate(dateString);
    return date.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch (error) {
    console.error("Error formatting time:", error, dateString);
    return "Invalid time";
  }
};

/**
 * Get the date key (YYYY-MM-DD) from a date string for calendar grouping
 * Uses local timezone to ensure events are grouped by the user's local date
 */
/**
 * Default start time when creating an event for a calendar day (YYYY-MM-DD).
 * Same calendar day as "now" → keep current clock time; otherwise 9:00 AM local.
 */
export const defaultDateTimeForCalendarDay = (dayKey: string): Date => {
  const parts = dayKey.split("-").map(Number);
  const y = parts[0];
  const m = parts[1];
  const d = parts[2];
  if (!y || !m || !d) {
    return new Date();
  }
  const now = new Date();
  const target = new Date(y, m - 1, d);
  const isToday =
    target.getDate() === now.getDate() &&
    target.getMonth() === now.getMonth() &&
    target.getFullYear() === now.getFullYear();
  if (isToday) {
    return new Date(y, m - 1, d, now.getHours(), now.getMinutes(), 0, 0);
  }
  return new Date(y, m - 1, d, 9, 0, 0, 0);
};

/** Short heading for a calendar day key, e.g. "Wed, Apr 10" */
export const formatCalendarDayHeading = (dateKey: string): string => {
  try {
    const parts = dateKey.split("-").map(Number);
    const y = parts[0];
    const mo = parts[1];
    const d = parts[2];
    if (!y || !mo || !d) return dateKey;
    const date = new Date(y, mo - 1, d);
    return date.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateKey;
  }
};

export const getDateKey = (dateString: string): string => {
  try {
    const date = parseDate(dateString);
    // Use local date instead of UTC to group events by user's local date
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    return `${year}-${month}-${day}`;
  } catch (error) {
    console.error("Error getting date key:", error, dateString);
    return "";
  }
};

/**
 * Format a conflict event date with duration
 */
export const formatConflictEventDate = (
  dateString: string,
  duration?: number
): string => {
  try {
    const startDate = parseDate(dateString);
    const endDate = duration
      ? new Date(startDate.getTime() + duration * 60000)
      : startDate;

    const startFormatted = `${startDate.toLocaleDateString("en-US", {
      weekday: "short",
      month: "short",
      day: "numeric",
    })}, ${startDate.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    })}`;

    if (duration && duration > 0) {
      const endFormatted = endDate.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
      return `${startFormatted} - ${endFormatted}`;
    }

    return startFormatted;
  } catch (error) {
    console.error("Error formatting conflict event date:", error, dateString);
    return "Invalid date";
  }
};

/**
 * Convert a Date object to ISO string while preserving the local timezone
 * This prevents unwanted UTC conversion when sending dates to the backend
 */
export const toLocalISOString = (date: Date): string => {
  // Get timezone offset in minutes and convert to milliseconds
  const timezoneOffset = date.getTimezoneOffset() * 60000;

  // Create a new date that represents the local time as if it were UTC
  const localDate = new Date(date.getTime() - timezoneOffset);

  // Get the ISO string and replace 'Z' with the actual timezone offset
  const isoString = localDate.toISOString();

  // Calculate timezone offset in hours and minutes
  const offsetHours = Math.floor(Math.abs(timezoneOffset) / (60 * 60000));
  const offsetMinutes = Math.floor(
    (Math.abs(timezoneOffset) % (60 * 60000)) / 60000
  );
  const offsetSign = timezoneOffset <= 0 ? "+" : "-";
  const offsetString = `${offsetSign}${offsetHours
    .toString()
    .padStart(2, "0")}:${offsetMinutes.toString().padStart(2, "0")}`;

  // Replace 'Z' with the actual timezone offset
  return isoString.replace("Z", offsetString);
};
