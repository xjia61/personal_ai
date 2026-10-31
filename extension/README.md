# Career Agent Chrome extension (local preview)

1. Open `chrome://extensions`, turn on Developer mode, choose **Load unpacked**,
   and select this `extension/` directory. No build or package installation is needed.
2. In Career Agent, configure Application Profile, approve a resume, and prepare
   an application from a saved job. Set its official Greenhouse or Lever URL first.
3. Choose **Download Extension Data**. This JSON contains contact information;
   keep it private and delete it when finished. It includes the chosen resume's
   name/version, not its content or any login/work-authorization information.
4. Open that exact official application page in your normal Chrome browser.
5. Open the extension popup, import the downloaded JSON, verify the selection,
   and click **Fill contact fields**. The imported data clears when the popup closes.
6. Review filled/skipped fields, upload the selected resume yourself, submit
   manually, then return to Career Agent and mark the application as applied.

Supported hosts: `boards.greenhouse.io`, `job-boards.greenhouse.io`, `jobs.lever.co`.
Only the main document is supported; open the direct ATS page for embedded forms.
The extension checks the selected posting's origin/path before filling. Existing
answers and ambiguous matches are skipped. No login, demographic, sponsorship,
salary, signature, checkbox, submit, or upload actions are automated.

Only `activeTab` and `scripting` permissions are requested, with no persistent
host access, storage, background scripts, backend connection, or analytics.
The export endpoint inherits the app's current local single-user behavior.
Do not expose the API publicly before authentication and per-user ownership exist.
Account linking and store distribution are future work.

Run unit tests with `npm test` here. Real DOM regression tests run from `backend/`:
`RUN_BROWSER_TESTS=1 .venv/bin/python -m pytest tests/test_extension_browser.py -q`.
