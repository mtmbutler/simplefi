# SimpleFi

- Manage a database of transactions
  - Upload and process CSV's from your bank
  - Download as a CSV or SQLite3 database
  - Re-upload each month to start where you left off
  - None of your data lives on anyone's servers
- Define your own matches to classify transactions
- View monthly category summaries
- Manage debt

### TODO

- Consolidate nav
    - Move bank creation to account creation
    - Move account holder creation to account creation
        - Does it need to be a model?
    - Move upload creation to account update
    - Rename 'Category' to 'Class' and make static
    - Rename 'Subcategory' to 'Category' and move to Pattern creation
    - Remove summaries from nav and add links at index
    - Rename index to 'Summary'
    - Make Login/Logout dynamic based on auth status
- Due diligence
    - Write tests
    - Write docs
- Set up data I/O capabilities for privacy
- Build a React.js concept
- Build REST API
- Build home page
