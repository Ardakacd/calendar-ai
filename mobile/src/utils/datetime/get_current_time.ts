import { DateTime } from 'luxon';
import * as Localization from 'expo-localization';



export function getUserDateTime(){
    // For example: 2025-06-28T13:45:00+03:00
    const currentDateTime = DateTime.local().setLocale(Localization.locale);

    const weekdayList = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    const weakdayIndex = currentDateTime.weekday - 1
    // Get current weekday (e.g., "Friday")
    const weekday = weakdayIndex < weekdayList.length ? weekdayList[weakdayIndex] : currentDateTime.weekdayLong // "Friday"

    // Get number of days in the current month
    const daysInMonth = currentDateTime.daysInMonth

    return {
        currentDateTime,
        weekday,
        daysInMonth
    }
}

