import { DiscordContextProvider } from '../hooks/useDiscordSdk'
import { Activity } from './Activity'
import './App.css'

/**
 * Set `authenticate` to true to enable Discord authentication.
 * You can also set the `scope` prop to request additional permissions.
 *
 * ```
 * <DiscordContextProvider authenticate scope={['identify', 'guilds', 'activity']}>
 *  <Activity />
 * </DiscordContextProvider>
 * ```
 */
export default function App() {
	return (
		<DiscordContextProvider authenticate scope={['identify', 'guilds', 'rpc.activities.write']}>
			<Activity />
		</DiscordContextProvider>
	)
}
