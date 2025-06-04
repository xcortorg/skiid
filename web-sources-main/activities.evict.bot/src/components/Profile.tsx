import { useDiscordSdk } from '../hooks/useDiscordSdk'

export function Profile() {
	const { accessToken, authenticated, discordSdk, error, session, status } = useDiscordSdk()

	return (
		<div className="p-4">
			<div className="max-w-md mx-auto bg-white rounded-lg shadow">
				<div className="p-6">
					<h2 className="text-2xl font-bold mb-4">Discord Profile</h2>
					
					<div className="space-y-3">
						<div>
							<span className="font-medium">Status:</span> {status}
						</div>
						<div>
							<span className="font-medium">Authenticated:</span> {authenticated ? 'Yes' : 'No'}
						</div>
						{error && (
							<div className="text-red-600">
								<span className="font-medium">Error:</span> {error}
							</div>
						)}
						{session && (
							<div>
								<span className="font-medium">User:</span> {session.user?.username}
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	)
}
