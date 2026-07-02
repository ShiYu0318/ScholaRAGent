import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en";
import zh from "./zh";

const LOCALE_KEY = "air.locale";

export function savedLocale(): string {
  return localStorage.getItem(LOCALE_KEY) ?? (navigator.language.startsWith("zh") ? "zh" : "en");
}

export function setLocale(locale: string) {
  localStorage.setItem(LOCALE_KEY, locale);
  void i18n.changeLanguage(locale);
}

void i18n.use(initReactI18next).init({
  resources: { en, zh },
  lng: savedLocale(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
