import { useEffect, useState } from 'react'
import { useDiscordSdk } from '../hooks/useDiscordSdk'

export const Activity = () => {
	const { authenticated, discordSdk, status, session, accessToken } = useDiscordSdk()
	const [playingData, setPlayingData] = useState<any>(null)
	const [isLoading, setIsLoading] = useState(true)
	const [error, setError] = useState<string | null>(null)
	const [currentTrackId, setCurrentTrackId] = useState<string | null>(null)
	const [authAttempts, setAuthAttempts] = useState(0)
	const [isInitializing, setIsInitializing] = useState(true)

	const log = {
		info: (msg: string, data?: any) =>
			console.log(`%c[Evict] %c${msg}`, 'color: #3b82f6; font-weight: bold', 'color: #94a3b8', data ? data : ''),
		success: (msg: string, data?: any) =>
			console.log(`%c[Evict] %c${msg}`, 'color: #22c55e; font-weight: bold', 'color: #86efac', data ? data : ''),
		error: (msg: string, error?: any) =>
			console.log(`%c[Evict] %c${msg}`, 'color: #ef4444; font-weight: bold', 'color: #fca5a5', error ? error : ''),
		warn: (msg: string, data?: any) =>
			console.log(`%c[Evict] %c${msg}`, 'color: #f59e0b; font-weight: bold', 'color: #fcd34d', data ? data : '')
	}

	const formatTime = (ms: number) => {
		const seconds = Math.floor(ms / 1000)
		const minutes = Math.floor(seconds / 60)
		const remainingSeconds = seconds % 60
		return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
	}

	useEffect(() => {
		const maxAttempts = 10
		const attemptInterval = 5000
		let timeoutId: NodeJS.Timeout

		const attemptAuth = async () => {
			if (authenticated) {
				log.success('Discord connection established')
				setIsLoading(false)
				setIsInitializing(false)
				setError(null)
				return true
			}

			if (!authenticated && !isInitializing) {
				try {
					log.info('Attempting to login to Discord...')
					await discordSdk.commands.authorize({
						client_id: '1323720110787268768',
						response_type: 'code',
						state: '',
						prompt: 'none',
						scope: [
							'identify',
							'guilds',
							'rpc.activities.write'
						]
					})
				} catch (error) {
					log.error('Login attempt failed:', error)
				}
			}

			if (authAttempts >= maxAttempts) {
				log.error('Failed to connect to Discord after multiple attempts')
				setError('Discord connection failed after multiple attempts')
				setIsLoading(false)
				setIsInitializing(false)
				return false
			}

			if (!isInitializing) {
				setAuthAttempts((prev) => prev + 1)
				log.info(`Attempting to connect to Discord (attempt ${authAttempts + 1}/${maxAttempts})`)
			}

			return false
		}

		const initializeConnection = async () => {
			const result = await attemptAuth()
			if (!result && authAttempts < maxAttempts) {
				timeoutId = setTimeout(() => {
					setIsInitializing(false)
					initializeConnection()
				}, attemptInterval)
			}
		}

		initializeConnection()

		return () => {
			if (timeoutId) clearTimeout(timeoutId)
		}
	}, [authenticated, authAttempts, discordSdk])

	useEffect(() => {
		if (!authenticated || !session?.user?.id) {
			if (authenticated === false) {
				log.warn('Not authenticated or missing user ID')
				setIsLoading(false)
			}
			return
		}

		let isMounted = true
		let lastUpdateTime = 0
		const minUpdateInterval = 1000 

		const updateDiscordActivity = async (data: any) => {
			if (!accessToken || !isMounted) return

			try {
				const now = Date.now()
				if (now - lastUpdateTime < minUpdateInterval) {
					return
				}
				lastUpdateTime = now

				if (!data.current) {
					log.info('No track playing, setting to idle')
					await discordSdk.commands.setActivity({
						activity: {
							type: 2,
							state: 'Idle',
							assets: {
								small_image: 'evict',
								small_text: 'evict music'
							}
						}
					})
					return
				}

				const title = data.current.title
				const artist = data.current.artist
				const defaultArt = 'https://cdn-images.dzcdn.net/images/cover/5e7b8670b572a110d4453e6ac94421d8/1000x1000-000000-80-0-0.jpg'

				let cleanTitle = title
				const artistPrefix = `${artist} - `
				if (title.startsWith(artistPrefix)) {
					cleanTitle = title.substring(artistPrefix.length)
				}

				const maxTitleLength = 32
				const maxArtistLength = 24
				
				cleanTitle = cleanTitle.length > maxTitleLength 
					? cleanTitle.substring(0, maxTitleLength - 3) + '...' 
					: cleanTitle
					
				const displayArtist = artist.length > maxArtistLength 
					? artist.substring(0, maxArtistLength - 3) + '...' 
					: artist

				const activity = {
					activity: {
						type: 2,
						state: data.voice_state?.paused ? `${cleanTitle} (Paused)` : cleanTitle,
						details: displayArtist,
						...(data.voice_state?.paused === false && {
							timestamps: {
								start: now - (data.current.position || 0),
								end: now + ((data.current.length || 0) - (data.current.position || 0))
							}
						}),
						assets: {
							large_image: data.current.album_art || defaultArt,
							large_text: `${artist} - ${title}`,
							small_image: 'evict',
							small_text: data.voice_state?.paused ? 'Paused' : 'Playing'
						}
					}
				}

				await discordSdk.commands.setActivity(activity)
				log.success('Discord activity updated successfully')
			} catch (error: any) {
				log.error('Failed to update Discord activity', error)
			}
		}

		const fetchPlaying = async () => {
			if (!isMounted) return

			try {
				setError(null)

				if (!playingData) {
					setIsLoading(true)
				}

				const response = await fetch(`/.proxy/api/playing/${session.user.id}`)
				if (!response.ok) {
					throw new Error(`Failed to fetch playing data (${response.status})`)
				}

				const data = await response.json()
				if (data.error) {
					throw new Error(data.error)
				}

				setCurrentTrackId(data.current?.id || `${data.current?.title}-${data.current?.artist}`)
				setPlayingData(data)
				await updateDiscordActivity(data)

			} catch (error: any) {
				log.error('Playback update failed', error)
				setError(error.message)
			} finally {
				if (isMounted) {
					setIsLoading(false)
				}
			}
		}

		log.info('Setting up playback monitoring...')
		fetchPlaying()
		const interval = setInterval(fetchPlaying, 5000) 

		return () => {
			isMounted = false
			clearInterval(interval)
			log.info('Cleaning up playback monitoring...')
		}
	}, [authenticated, discordSdk, session?.user?.id, accessToken, currentTrackId])

	return (
		<div className="container">
			{isLoading ? (
				<div className="loading-state">
					<div className="loading-indicator">
						<div className="loading-dot" />
						<span className="loading-text">
							{isInitializing ? 'Initializing...' : `Connecting to Discord (${authAttempts}/${10})`}
						</span>
					</div>
				</div>
			) : error ? (
				<div className="error-state">
					<div className="error-indicator">
						<div className="error-dot" />
						<span className="error-text">{error}</span>
					</div>
				</div>
			) : !authenticated ? (
				<div className="auth-state">
					<div className="auth-indicator">
						<div className="auth-dot" />
						<span className="auth-text">Not connected to Discord</span>
					</div>
				</div>
			) : (
				<div className="content">
					<div className="status-card">
						<div className="status-left">
							<div className="status-indicator connected" />
							<span>Connected to Discord</span>
						</div>
						<span className="status-right">{status}</span>
					</div>

					{playingData?.current && (
						<div>
							<div className="now-playing">
								<div className="now-playing-content">
									<div className="now-playing-header">
										<div className="now-playing-dot" />
										<span>NOW PLAYING</span>
									</div>
									
									<div className="track-info">
										<div className="track-number">#1</div>
										<div className="track-details">
											<h2>{playingData.current.title}</h2>
											<p>{playingData.current.artist}</p>
											{playingData.current.album && (
												<p className="album-name">{playingData.current.album}</p>
											)}
										</div>
										<div className="track-controls">
											<div className="progress-container">
												<div 
													className="progress-bar" 
													style={{ 
														width: `${(playingData.current.position / playingData.current.length) * 100}%` 
													}}
												/>
												<div className="time-display">
													<span>{formatTime(playingData.current.position)}</span>
													<span>{formatTime(playingData.current.length)}</span>
												</div>
											</div>
											<div className="playback-controls">
												<div className="volume-control">
													<input 
														type="range" 
														min="0" 
														max="100" 
														value={playingData.voice_state?.volume || 0}
														className="volume-slider"
														readOnly
													/>
													<span>{playingData.voice_state?.volume}%</span>
												</div>
												<button 
													className={`loop-control ${playingData.voice_state?.loop_mode.toLowerCase()}`}
												>
													{playingData.voice_state?.loop_mode}
												</button>
											</div>
										</div>
									</div>
								</div>
							</div>

							{playingData.queue?.length > 0 && (
								<div className="queue-container">
									<div className="queue-header">
										<div className="queue-title">
											<div className="queue-dot" />
											<span>QUEUE</span>
										</div>
										<span className="queue-count">{playingData.queue_length} tracks</span>
									</div>
									<div className="queue-list">
										{playingData.queue.slice(0, 50).map((track: any, i: number) => (
											<div key={i} className="queue-item">
												<div className="track-number">#{i + 2}</div>
												<div className="queue-track-info">
													<div className="queue-track-title">{track.title}</div>
													<div className="queue-track-artist">{track.artist}</div>
													{track.album && (
														<div className="queue-track-album">{track.album}</div>
													)}
												</div>
												<div className="track-duration">{formatTime(track.length)}</div>
											</div>
											))}
									</div>
								</div>
							)}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
