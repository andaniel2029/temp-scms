### Todo 

#### From spreadsheet

- [x] Order page - show last 30 days
- [x] Order page - decending sort creation date
- [x] (tested, works) Order page - The Customer Reference column listed below doesn't appear on non-test (real client pages)--we want to have this data be displayed by default--it's the Transaction ID value for imported orders and the Shipment Identifier/Reference value for manually entered orders
- [x] Order page - Add additional search filter options to the existing date range option (which should be better labeled as Date Range
    - [x] Recipient
    - [x] Customer PO#/Transaction #
    - [x] Tracking #
- [x] Order page - optionally add a paging feature
- [x] Order page - Export order - csv export on custom date range not working
- [x] Propagating supplied Client's "customer PO #" to FedEx shipping record
    - Capture, store, and include the Customer PO# / Transaction # in the EasyPost-FedEx data record transmission so this value is passed to FedEx and stored on the FedEx shipment record.
    - For customers uploading order files via the CSV template, which is the more common method, customers are including this PO Number value is the Transaction ID field.
    - For manually entered orders, it is the Shipment Identifier/Reference field.
    - Might be able to use the Reference field in EasyPost for mapping this value to the FedEx's Original Ref#3/PO Number field (but this needs to be verified).
- [x] User page - Add a Client (User) Status Code attribute to the User record to allow the PB (Admin) User abiliity to set a status of a Client account as Active or Inactive.
- [x] User page - Include Status as a column on Users page view, and allow Admin user the ability to also filter view by Status: All, Active, Inactive (Default is Active)."
- [x] (BIG TASK) Order creation - Check BL5
    - Step 1
    - [x] Create order page - recipient drop down dynamic and add option at first
    - Step 2
    - [x] Remove Adjust Label, and relabel Adjust Quantity to Save
    - [x] Add a check to ensure that either Cases or Units Quantity has minimally a value of 1 before completing order
    - [x] Move the signature required options to the next step (during select shipping method)
    - [x] Re-label Shipment Items Completed to Order Complete
    - Step 3
    - [x] Only display List Rates
    - [x] Add Signature Required  options from previous step to this step
    - [x] Fix Recipient information not being displayed on this step
    - Step 4
    - [x] Fix Recipient information not being displayed on this step
    - [x] Show summary of order items and shipping information, along with currently displayed details
     
- [x] Sign in page - center align form
- [x] Order upload history - UI improvements
    1) [x] Only show the most recent 30-days of upload history by default
    2) [x] Default list order to by created date - descending (most recent 1st)
    3) [x] Add a Date Range search option (reference Range search on Orders view) 

#### Notes
##### Current work
- on order creation page, the recipient select is not select2, but still loads 10000 records and searches in js. Should change to AJAX

##### Previous dev backlog
- Recipient upload is not supported at all in code
- Inventory.ship_ready has a todo saying `We don't have the spec for what this field *should* be.`

#### From job desc

- [x] Fix the custom date range filtering on the export shipped orders option as today when entering a from-to date range, an export file without any data is generated. All of the other options work as expected.
- [ ] Enable Clients ability to insert orders via an API.
- [ ] Enable Client User ability to register for SCMS User Account.
- [ ] Enable Client User ability to perform a self-serve password reset.
- [ ] Enable Client User ability to perform a self-serve username reminder.
- [ ] Enable Client User ability to query Order records by primary status: Pending, Shipped, or Cancelled.
- [x] Allow PB (Admin) User abiliity to set a status of a Client account
- [ ] Enable PB (Admin) User generate an email notification to all Client contacts (i.e. new feature added to system, FedEx surcharge increase, etc.)
- [ ] Add ability to use a 2nd warehouse location
- [ ] Auditing
- [ ] Apply UD improvements
- [x] Streamline manual order entry process
- [x] Capture, store, and include the Customer PO # in the EasyPost-FedEx data record transmission so we have this value when extracting FedEx reporting.
- [ ] Enable PB (Admin) User ability to generate a cycle count report.
- [ ] Enable PB (Admin) User ability to generate shipping details for a given client for a given date range, which is used as billing back up details.
- [ ] Enable PB (Admin) User ability to process a returned shipments.
- [ ] Enable PB (Admin) User ability to automatically process a reship for a previously shipped order.
- [ ] Add EDI and FTP capabilities
- [ ] Add additional statusing
- [ ] Barcode scanning
- [ ] Stock, Pick locations
- [ ] Lot #s
- [ ] Process orders/shipments for Cross-dock clients.
- [ ] Add ability to generate Return Labels
- [ ] Pick Tickets Enhancements
- [ ] Packing slips Enancements

-----------------

The hosting on AWS should be almost nothing for first year on free tier since I am running the service on a free tier server. 

Also, if you are considering another phase of improvements, here is some technical debt that I found during working on the project and wasn't able to get rid of you might want to consider adding to it:
- (Important) Currently the uploaded files are stored on the local storage, which is not recommended. We should migrate to s3 for the storage of these files to ensure security and scalability, also making it more sensible since we are now on the aws platform for hosting. We can also enable client side upload of files to s3
- (Important) A lot of the tasks in the app that currently happen during requests (Emails, File Processing etc.) should be done by an aysnc worker 
- The current app structures doesn't break down the views into submodules. It might help to do so to ensure better maintainability of the code in the future.
- The current order processing workflow needs to be reworked and simplified in the backend.

For design:
- We can move to a better and modern design replacing bootstrap3 based theme to a modern UI framework. This would also mean getting rid of wtforms to process forms and having greater control over them.
- The order flow can be redesigned as a better multi step process.
- The homepage for prioritybiz.com can be redesigned.

For scaling:
- (Important) The database in the current setup runs on the same machine as the web server, which can be moved to an independent server or aws hosted mysql, and scaling it independently in the future if needed, with auto backups in place
- (Suggested) Currently, there is a single instance running on a single server that serves the site (along with running the database and workers), which means the sites goes down if the server goes down. This can be avoided by having 2-3 small replica servers for the applications and a load balancer with health checks to make sure that clients always get served (HA - High Availability)
- In future a redis/memcache based cache can be added to serve pages faster

Previous dev backlog:
- Recipient upload is not supported at all in code
- Inventory.ship_ready has a todo saying `We don't have the spec for what this field *should* be.`

From your initial project requirements draft, I understand some of the tasks are still incomplete. I also have these tasks in which I understand what needs to be done and can get it on it fast it you want:
- Enable Clients ability to insert orders via an API. (This also aligns with the above suggested improvement in the order creation process, as this API would enable a JS based solution)
- Enable Client User ability to register for SCMS User Account.
- Enable Client User ability to perform a self-serve password reset.
- Enable Client User ability to perform a self-serve username reminder.
- Enable Client User ability to query Order records by primary status: Pending, Shipped, or Cancelled.
- Enable PB (Admin) User generate an email notification to all Client contacts (i.e. new feature added to system, FedEx surcharge increase, etc.)

