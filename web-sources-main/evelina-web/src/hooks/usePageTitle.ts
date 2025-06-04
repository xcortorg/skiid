import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

interface PageMeta {
  title: string;
  description: string;
}

export function usePageTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    const baseTitle = 'Evelina';
    let pageMeta: PageMeta = {
      title: '',
      description: 'a premium discord bot giving you the resources to create a powerful and versatile community at the tip of your fingers.'
    };

    // Dashboard Routes
    if (pathname.startsWith('/staff')) {
      if (pathname === '/staff') {
        pageMeta = {
          title: 'Staff',
          description: 'Here you can see the overview of the staff team.'
        };
      }
    }
    // Public Routes
    else switch (pathname) {
      case '/':
        pageMeta = {
          title: 'Discord Bot',
          description: 'a premium discord bot giving you the resources to create a powerful and versatile community at the tip of your fingers.'
        };
        break;
      case '/commands':
        pageMeta = {
          title: 'Commands',
          description: 'Explore all available commands and their usage with Evelina Discord bot.'
        };
        break;
      case '/status':
        pageMeta = {
          title: 'Status',
          description: 'Check the real-time status and performance of Evelina Discord bot.'
        };
        break;
      case '/team':
        pageMeta = {
          title: 'Team',
          description: 'Meet the dedicated team behind Evelina Discord bot.'
        };
        break;
      case '/premium':
        pageMeta = {
          title: 'Premium',
          description: 'Unlock premium features and enhance your Discord server with Evelina.'
        };
        break;
      case '/terms':
        pageMeta = {
          title: 'Terms of Service',
          description: 'Read our terms of service and usage guidelines for Evelina Discord bot.'
        };
        break;
      case '/economy':
        pageMeta = {
          title: 'Economy Rules',
          description: 'Read our terms of service and usage guidelines for Evelina Discord bot.'
        };
        break;
      case '/privacy':
        pageMeta = {
          title: 'Privacy Policy',
          description: 'Learn how we protect and handle your data at Evelina Discord bot.'
        };
        break;
      case '/refund':
        pageMeta = {
          title: 'Refund Policy',
          description: 'Understand our refund policy and terms for Evelina Discord bot services.'
        };
        break;
      case '/contact':
        pageMeta = {
          title: 'Contact',
          description: 'Get in touch with our support team for any questions about Evelina Discord bot.'
        };
        break;
      case '/embed':
        pageMeta = {
          title: 'Embed Builder',
          description: 'Create beautiful Discord embeds with our visual editor.'
        };
        break;
      case '/templates':
        pageMeta = {
          title: 'Embed Templates',
          description: 'Browse and use pre-made Discord embed templates for your server.'
        };
        break;
      case '/feedback':
        pageMeta = {
          title: 'Community Feedback',
          description: 'See what our users are saying about Evelina Discord bot.'
        };
        break;
      case '/avatars':
        pageMeta = {
          title: 'Avatar History',
          description: 'Browse avatar history for Discord users.'
        };
        break;
      case '/discord':
        pageMeta = {
          title: 'Discord Server',
          description: 'Join the official Evelina Discord server.'
        };
        break;
      case '/invite':
        pageMeta = {
          title: 'Bot Invite',
          description: 'Add Evelina Discord bot to your server.'
        };
        break;
      case '/features/automod':
        pageMeta = {
          title: 'Auto Moderation',
          description: 'Keep your Discord server safe with advanced auto-moderation features.'
        };
        break;
      case '/features/tickets':
        pageMeta = {
          title: 'Ticket System',
          description: 'Manage support tickets efficiently with our advanced ticket system.'
        };
        break;
      case '/features/welcome':
        pageMeta = {
          title: 'Welcome System',
          description: 'Create personalized welcome experiences for new members in your Discord server.'
        };
        break;
      case '/features/music':
        pageMeta = {
          title: 'Music Player',
          description: 'High-quality music playback with playlist support for your Discord server.'
        };
        break;
      case '/features/economy':
        pageMeta = {
          title: 'Economy System',
          description: 'Engage your community with an advanced virtual economy system.'
        };
        break;
      case '/features/giveaways':
        pageMeta = {
          title: 'Giveaway System',
          description: 'Create and manage engaging giveaways for your Discord community.'
        };
        break;
      case '/features/voicemaster':
        pageMeta = {
          title: 'Voice Master',
          description: 'Create and manage custom voice channels with full control.'
        };
        break;
      case '/features/vanityroles':
        pageMeta = {
          title: 'Vanity Roles',
          description: 'Custom roles for server boosters and special members.'
        };
        break;
      case '/features/buttonroles':
        pageMeta = {
          title: 'Button Roles',
          description: 'Create interactive role selection menus with custom buttons.'
        };
        break;
      case '/features/leveling':
        pageMeta = {
          title: 'Leveling System',
          description: 'Engage your community with text and voice leveling.'
        };
        break;
      case '/features/bump':
        pageMeta = {
          title: 'Bump Reminder',
          description: 'Never miss a bump with our automated reminder system.'
        };
        break;
      // Handle category-specific command routes
      default:
        if (pathname.startsWith('/commands/')) {
          const categoryParam = pathname.split('/commands/')[1];
          const formattedCategory = categoryParam.charAt(0).toUpperCase() + categoryParam.slice(1);
          pageMeta = {
            title: `${formattedCategory} Commands`,
            description: `Explore ${formattedCategory.toLowerCase()} commands and their usage with Evelina Discord bot.`
          };
          break;
        }
        
        // For user avatar pages
        if (pathname.startsWith('/avatars/')) {
          const userId = pathname.split('/avatars/')[1];
          pageMeta = {
            title: `Avatar History - User ${userId}`,
            description: `View avatar history for user ${userId}.`
          };
        } else {
          pageMeta = {
            title: '404 Not Found',
            description: "The page you're looking for doesn't exist or has been moved."
          };
        }
    }

    // Update document title
    document.title = pageMeta.title ? `${baseTitle} - ${pageMeta.title}` : baseTitle;

    // Update meta tags
    const metaTags = {
      description: document.querySelector('meta[name="description"]'),
      ogTitle: document.querySelector('meta[property="og:title"]'),
      ogDescription: document.querySelector('meta[property="og:description"]'),
      ogUrl: document.querySelector('meta[property="og:url"]'),
      ogImage: document.querySelector('meta[property="og:image"]'),
      favicon: document.querySelector('link[rel="icon"]'),
      appleTouchIcon: document.querySelector('link[rel="apple-touch-icon"]')
    };

    if (metaTags.description) {
      metaTags.description.setAttribute('content', pageMeta.description);
    }
    if (metaTags.ogTitle) {
      metaTags.ogTitle.setAttribute('content', `${baseTitle} - ${pageMeta.title}`);
    }
    if (metaTags.ogDescription) {
      metaTags.ogDescription.setAttribute('content', pageMeta.description);
    }
    if (metaTags.ogUrl) {
      metaTags.ogUrl.setAttribute('content', `https://evelina.bot${pathname}`);
    }
    if (metaTags.ogImage) {
      metaTags.ogImage.setAttribute('content', 'https://r.emogir.ls/evelina-pfp.png');
    }
    if (metaTags.favicon) {
      metaTags.favicon.setAttribute('href', 'https://r.emogir.ls/evelina-pfp.png');
    }
    if (metaTags.appleTouchIcon) {
      metaTags.appleTouchIcon.setAttribute('href', 'https://r.emogir.ls/evelina-pfp.png');
    }
  }, [pathname]);
}