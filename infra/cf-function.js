// Viewer-request function on the default (S3) behavior, cloudfront-js-2.0 runtime.
// The S3 REST origin behind OAC has no index documents, so map clean URLs to the
// index.html objects that build_site.py writes:
//   /            -> /index.html
//   /try/        -> /try/index.html
//   /how-it-works -> /how-it-works/index.html
// Anything with a file extension in its last segment (/assets/app.css) is left alone,
// including the in-browser OCR files: /vendor/tesseract/*.wasm, *.wasm.js and
// lang/*.traineddata.gz pass through unchanged (checked in infra/README-infra.md, Verify).
// template.yaml inlines this code in UriRewriteFunction. scripts/deploy.sh compares the
// two (ignoring comment lines and blank lines) and refuses to deploy when they drift.
function handler(event) {
  var request = event.request;
  var uri = request.uri;

  if (uri.endsWith('/')) {
    request.uri = uri + 'index.html';
  } else if (uri.lastIndexOf('.') < uri.lastIndexOf('/') + 1) {
    request.uri = uri + '/index.html';
  }
  return request;
}
