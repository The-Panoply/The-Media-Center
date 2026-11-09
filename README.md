# The-Media-Center

## Home Screen application and appearance

- `manifest.webmanifest` uses relative identity, start URL and scope for this GitHub Pages project.
- `icons/` contains opaque 180, 192 and 512 pixel adaptations of the existing navy/gold favicon. The browser favicon is unchanged.
- On iPhone/iPad, open the published HTTPS site in Safari and use Share → Add to Home Screen; enable Open as Web App if offered.
- Appearance follows `prefers-color-scheme`; no manual switch or saved theme override is introduced.
- No service worker or offline content cache is registered. Content continues through the existing online publication workflow; there is no app cache to version or clear.
- Keep the manifest identity and project path stable when publishing updates. A future move needs a separate migration plan.
