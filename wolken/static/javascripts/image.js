$(function() {
  if (!$("body#image").length) { return; }

  var hasPushState = (typeof history.pushState !== 'undefined'),
      viewport     = $(window),
      body         = $("body"),
      content      = $("#content"),
      image        = $("img"),
      headerHeight = $("h2").height(),
      full         = { height: 0, width: 0 },
      max          = { height: 0, width: 0 };


  // Calculate the maximum width and height available to the content based on
  // the viewport size and header height leaving a 10% padding around the
  // content. Add `max-height` to the image so it fits comfortably within the
  // viewable area and trigger `"zoom"`.
  viewport.resize(function() {
    max.width  = Math.floor(viewport.width()  * 0.9);
    max.height = Math.floor(viewport.height() * 0.9) - headerHeight;

    if (!body.is(".zoomed-in")) {
      image
        .css({ maxHeight: max.height })
        .trigger("zoom");
    }

    content.trigger("center");
  });

  image

    // Check the current maximum image dimensions and add the class
    // `"zoomed-out"` if the image is too large to fit within the viewport
    // otherwise remove it. Trigger `"center"` to center the image vertically.
    // Ignore image resizing when the image is zoomed in or not yet
    // initialized.
    .bind("zoom", function() {
      if (body.is(".zoomed-in") || !image.data("initialized")) { return; }

      if (full.width > max.width || full.height > max.height) {
        body.addClass("zoomed-out");
      } else {
        body.removeClass("zoomed-out");
      }

      content.trigger("center");
    })

    // Resize the image to its full size and center it.
    .bind("zoom-in", function() {
      body
        .addClass("zoomed-in")
        .removeClass("zoomed-out");

      content.trigger("center");
    })

    // Resize the image to fit within the viewport.
    .bind("zoom-out", function() {
      body.removeClass("zoomed-in");
      viewport.trigger("resize");
    })

    // Handle clicks on the image to toggle its zoom state. Ignore clicks if
    // the image fully fits within the viewport. If the browser supports
    // pushState, append `/o` to the path when zooming the image in and remove
    // it when zooming out. This logic would be better served as a link
    // wrapping the image.
    .click(function() {
      if (body.is(".zoomed-in")) {
        if (hasPushState) {
          var path = location.pathname.match(/(.+)\/o$/)[1];
          history.pushState(null, null, path);
        }

        image.trigger("zoom-out");
      } else if (body.is(".zoomed-out")) {
        if (hasPushState) {
          var path = location.pathname + "/o";
          history.pushState(null, null, path);
        }

        image.trigger("zoom-in");
      }
    });

  // Center the content vertically in the viewport by modifying the content
  // element's top padding. Must account for the header height if its visible.
  content.bind("center", function() {
    var viewportSize = viewport.height();

    if (!image.data("initialized")) {

      // Let CSS handle the initialize image position when the default is to
      // display the original image size.
      if (body.is(".zoomed-in")) { return; }

      viewportSize = viewportSize - max.height - headerHeight;
    } else {
      viewportSize -= content.height();

      if (body.is(".zoomed-out")) {
        viewportSize -= headerHeight;
      }
    }

    var top = Math.max(0, Math.floor(viewportSize / 2));
    content.css({ paddingTop: top });
  });


  // Create a temporary image to determine the full size of the main image.
  // Mark the image as initialized and trigger its `"zoom"` event.
  var tmpImage = $("<img/>")
                   .attr("src", image.attr("src"))
                   .load(function() {
                     full.width   = this.width;
                     full.height  = this.height;

                     image
                       .data("initialized", true)
                       .trigger("zoom");
                   });

  // Manually trigger the `"load"` event on the temp image if its cached.
  if (tmpImage[0].complete) {
    tmpImage.trigger("load");
  }

  viewport

    // Listen for `"popstate"` on image drops. Trigger `"zoom-in"` on the
    // image if the current path is `/o` or `"zoom-out"` otherwise.
    .bind("popstate", function() {
      if (location.pathname.match(/.+\/o$/)) {
        image.trigger("zoom-in");
      } else {
        image.trigger("zoom-out");
      }
    })

    // Trigger `"popstate"` to kick start image zooming.
    .trigger("popstate");
});
