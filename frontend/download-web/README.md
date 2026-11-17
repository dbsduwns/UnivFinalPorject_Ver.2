# KNU Campus Android download page

Deploy this folder as a separate Vercel project. The deployed page URL is the stable address encoded into the QR code. The page reads the latest active Android release from `/api/app-updates/android?current_version_code=0` and links the download button to its `apk_url`.

Recommended Vercel project name: `knu-campus-download`
