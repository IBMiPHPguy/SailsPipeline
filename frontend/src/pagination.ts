export const DEFAULT_PAGE_SIZE = 10;
export const PAGE_SIZE_OPTIONS = [10, 15, 25, 50, 100] as const;

export type PageSizeOption = (typeof PAGE_SIZE_OPTIONS)[number];

export function normalizePageSize(size: number): PageSizeOption {
  if ((PAGE_SIZE_OPTIONS as readonly number[]).includes(size)) {
    return size as PageSizeOption;
  }
  return DEFAULT_PAGE_SIZE;
}
