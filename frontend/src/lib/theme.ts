export const THEME_STORAGE_KEY = "shirube-theme";
export const DARK_THEME = "dark";

export const THEME_SCRIPT = `try{if(localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)})===${JSON.stringify(DARK_THEME)})document.documentElement.dataset.theme=${JSON.stringify(DARK_THEME)}}catch{}`;
