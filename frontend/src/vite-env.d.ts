/// <reference types="vite/client" />

/* ===== CSS Module type declaration ===== */
declare module '*.module.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}
