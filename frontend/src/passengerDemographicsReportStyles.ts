export const PASSENGER_DEMOGRAPHICS_HEADER_STYLE = {
  fill: "F8FAFC",
  fontColor: "486581",
  bottomBorder: "E2E8F0",
} as const;

export const PASSENGER_DEMOGRAPHICS_BODY_STYLE = {
  fill: "FFFFFF",
  nameFontColor: "243B53",
  textFontColor: "102A43",
  emptyFontColor: "627D98",
  border: "E2E8F0",
} as const;

export const PASSENGER_QUALIFIER_EXPORT_STYLES: Record<string, { fontColor: string }> = {
  Military: { fontColor: "1864AB" },
  Educator: { fontColor: "087F5B" },
  "First Responder": { fontColor: "D9480F" },
  "55+ (Senior)": { fontColor: "5F3DC4" },
};

export const PASSENGER_QUALIFIER_EXPORT_DEFAULT_STYLE = {
  fontColor: "486581",
} as const;
