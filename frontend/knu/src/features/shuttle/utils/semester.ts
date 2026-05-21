export const getCurrentSemester = (date = new Date()) => {
  const year = date.getFullYear();
  const month = date.getMonth() + 1;

  if (month >= 3 && month <= 8) {
    return `${year}-1`;
  }

  if (month >= 9 && month <= 12) {
    return `${year}-2`;
  }

  return `${year - 1}-2`;
};