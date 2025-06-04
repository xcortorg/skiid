export async function GET(request: Request) {
  try {
    const url = new URL(request.url)
    const imageUrl = url.searchParams.get('url')

    if (!imageUrl) {
      return new Response('Missing URL parameter', { status: 400 })
    }

    console.log('Fetching image from:', imageUrl)

    const response = await fetch(imageUrl, {
      headers: {
        'Accept': 'image/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      }
    })
    
    if (!response.ok) {
      console.error('Failed to fetch image:', response.status, response.statusText)
      return new Response('Failed to fetch image', { status: response.status })
    }

    const contentType = response.headers.get('content-type')
    const imageBuffer = await response.arrayBuffer()

    console.log('Successfully fetched image:', {
      size: imageBuffer.byteLength,
      type: contentType
    })

    return new Response(imageBuffer, {
      headers: {
        'Content-Type': contentType || 'image/jpeg',
        'Cache-Control': 'public, max-age=3600',
        'Access-Control-Allow-Origin': '*'
      }
    })
  } catch (error) {
    console.error('Image proxy error:', error)
    return new Response('Internal Server Error', { status: 500 })
  }
}
