# PSX Dividend Tracker

Static page (`index.html`) that reads `data.json`. A GitHub Action refreshes
`data.json` twice a day from PSX Terminal, and GitHub Pages serves the site.

## One-time setup
1. Create a new GitHub repo and upload all these files (keep the `.github` and `scripts` folders).
2. Repo **Settings > Pages**: Source = "Deploy from a branch", Branch = `main`, folder = `/ (root)`.
3. Repo **Settings > Actions > General > Workflow permissions**: choose "Read and write permissions".
4. **Actions** tab > "Update dividend data" > **Run workflow**. Open the run log and check
   the "Sample /dividends/MARI response" line and the "Parsed payouts / upcoming" counts.

Your site will be at `https://<username>.github.io/<repo>/`.

## Notes
- If the API cannot be read or looks wrong, the script stops and keeps the old `data.json`.
- Company name and the Shariah flag are kept from the previous `data.json` (`meta`).
  Newly appearing symbols get no name and Shariah = 0; edit `meta` in `data.json` to fix.
- GitHub pauses scheduled workflows after 60 days with no repo activity; press
  "Run workflow" once to wake it up if that happens.
