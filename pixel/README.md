# pixel/

`pixel.js` source (vanilla TS) bundled to the API's `/px.js`. Built in **M5**
(see `ctv-platform-spec/docs/08-tracking-attribution.md`): a tiny tracker that
posts `page_view` / `lead` / `add_to_cart` / `purchase` events to the public
`POST /e` ingest endpoint, keyed by the advertiser's pixel public key.
