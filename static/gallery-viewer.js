(function () {
  const galleryItems = Array.from(document.querySelectorAll("[data-gallery-item]"))
  const viewer = document.getElementById("gallery-viewer")

  if (!viewer || viewer.dataset.initialized === "true") {
    return
  }

  viewer.dataset.initialized = "true"

  const viewerShell = viewer.querySelector(".gallery-viewer-media-shell")
  const viewerImage = document.getElementById("gallery-image")
  const viewerVideo = document.getElementById("gallery-video")
  const viewerTitle = document.getElementById("gallery-title")
  const viewerCount = document.getElementById("gallery-count")
  const closeButton = document.getElementById("gallery-close")
  const prevButton = document.getElementById("gallery-prev")
  const nextButton = document.getElementById("gallery-next")
  const zoomInButton = document.getElementById("gallery-zoom-in")
  const zoomOutButton = document.getElementById("gallery-zoom-out")
  const zoomResetButton = document.getElementById("gallery-zoom-reset")
  const itemLabel = viewer.dataset.itemLabel || "Archivo"
  let currentIndex = 0
  let currentZoom = 1
  let touchStartX = 0
  let touchEndX = 0

  function applyZoom() {
    viewerImage.style.transform = `scale(${currentZoom})`
    zoomResetButton.textContent = `${Math.round(currentZoom * 100)}%`
  }

  function resetZoom() {
    currentZoom = 1
    applyZoom()
  }

  function updateCursor() {
    viewerShell.style.cursor = currentZoom > 1 ? "zoom-out" : "zoom-in"
  }

  function updateZoom(delta) {
    currentZoom = Math.min(3, Math.max(1, currentZoom + delta))
    applyZoom()
    updateCursor()
  }

  function renderGalleryItem(index) {
    const safeIndex = (index + galleryItems.length) % galleryItems.length
    const item = galleryItems[safeIndex]
    currentIndex = safeIndex
    const itemType = item.dataset.type || "image"
    const itemSrc = item.dataset.src || item.href
    resetZoom()

    if (itemType === "video") {
      viewerImage.classList.add("is-hidden")
      viewerVideo.classList.remove("is-hidden")
      viewerVideo.src = itemSrc
      viewerVideo.currentTime = 0
      zoomInButton.disabled = true
      zoomOutButton.disabled = true
      zoomResetButton.disabled = true
      viewerShell.style.cursor = "default"
    } else {
      viewerVideo.pause()
      viewerVideo.removeAttribute("src")
      viewerVideo.load()
      viewerVideo.classList.add("is-hidden")
      viewerImage.classList.remove("is-hidden")
      viewerImage.src = itemSrc
      zoomInButton.disabled = false
      zoomOutButton.disabled = false
      zoomResetButton.disabled = false
      updateCursor()
    }

    viewerTitle.textContent = item.dataset.fileName || item.dataset.title || itemLabel
    viewerCount.textContent = `${itemLabel} ${safeIndex + 1} de ${galleryItems.length}`
  }

  function openGallery(index) {
    if (!galleryItems.length) return
    renderGalleryItem(index)
    viewer.classList.add("is-open")
    viewer.setAttribute("aria-hidden", "false")
    document.body.style.overflow = "hidden"
    closeButton.focus()
  }

  function closeGallery() {
    viewer.classList.remove("is-open")
    viewer.setAttribute("aria-hidden", "true")
    viewerImage.removeAttribute("src")
    viewerVideo.pause()
    viewerVideo.removeAttribute("src")
    viewerVideo.load()
    resetZoom()
    document.body.style.overflow = ""
  }

  function stepGallery(direction) {
    if (!galleryItems.length) return
    renderGalleryItem(currentIndex + direction)
  }

  galleryItems.forEach((item, index) => {
    item.addEventListener("click", event => {
      event.preventDefault()
      openGallery(index)
    })
  })

  closeButton.addEventListener("click", closeGallery)
  prevButton.addEventListener("click", () => stepGallery(-1))
  nextButton.addEventListener("click", () => stepGallery(1))
  zoomInButton.addEventListener("click", () => updateZoom(0.25))
  zoomOutButton.addEventListener("click", () => updateZoom(-0.25))
  zoomResetButton.addEventListener("click", resetZoom)

  viewer.addEventListener("click", event => {
    if (event.target === viewer) {
      closeGallery()
    }
  })

  viewerShell.addEventListener("dblclick", () => {
    if (viewerImage.classList.contains("is-hidden")) return
    currentZoom = currentZoom === 1 ? 2 : 1
    applyZoom()
    updateCursor()
  })

  viewerShell.addEventListener(
    "wheel",
    event => {
      if (viewerImage.classList.contains("is-hidden")) return
      event.preventDefault()
      updateZoom(event.deltaY < 0 ? 0.2 : -0.2)
    },
    { passive: false }
  )

  viewerShell.addEventListener(
    "touchstart",
    event => {
      touchStartX = event.changedTouches[0].clientX
    },
    { passive: true }
  )

  viewerShell.addEventListener(
    "touchend",
    event => {
      touchEndX = event.changedTouches[0].clientX
      const deltaX = touchEndX - touchStartX
      if (Math.abs(deltaX) < 50) return
      if (deltaX > 0) {
        stepGallery(-1)
      } else {
        stepGallery(1)
      }
    },
    { passive: true }
  )

  document.addEventListener("keydown", event => {
    if (!viewer.classList.contains("is-open")) return
    if (event.key === "Escape") closeGallery()
    if (event.key === "ArrowLeft") stepGallery(-1)
    if (event.key === "ArrowRight") stepGallery(1)
  })
})()
