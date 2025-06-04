export function verifyBackupCode(code: string, storedCodes: string): boolean {
  if (!storedCodes) return false;
  const codes = JSON.parse(storedCodes);
  return codes.includes(code);
}
