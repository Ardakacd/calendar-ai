export const formatDuration = (duration?: number) => {
    if (!duration || duration === 0) return 'Belirtilmedi';
    const hours = Math.floor(duration / 60);
    const minutes = duration % 60;
    
    if (hours > 0 && minutes > 0) {
      return `${hours} saat ${minutes} dakika`;
    } else if (hours > 0) {
      return `${hours} saat`;
    } else {
      return `${minutes} dakika`;
    }
  };

export const formatLocation = (location?: string) => {
    if (!location) return 'Belirtilmedi';
    return location;
  };