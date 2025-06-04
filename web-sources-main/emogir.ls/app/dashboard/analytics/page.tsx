"use client";

import { useState, useEffect } from "react";
import { StatCard } from "@/components/ui/stat-card";
import { DataCard } from "@/components/ui/data-card";
import {
  IconDeviceLaptop,
  IconDeviceMobile,
  IconBrowser,
  IconWorld,
  IconLink,
  IconCopy,
  IconCheck,
  IconArrowUpRight,
  IconChartBar,
  IconUsers,
  IconClick,
  IconClock,
} from "@tabler/icons-react";
import { AnalyticsGraph } from "@/components/ui/analytics-graph";
import { useSession } from "next-auth/react";
import { Device } from "@/types/analytics";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/toast-provider";

const COUNTRY_NAMES: { [key: string]: string } = {
  AF: "Afghanistan",
  AL: "Albania",
  DZ: "Algeria",
  AS: "American Samoa",
  AD: "Andorra",
  AO: "Angola",
  AI: "Anguilla",
  AQ: "Antarctica",
  AG: "Antigua and Barbuda",
  AR: "Argentina",
  AM: "Armenia",
  AW: "Aruba",
  AU: "Australia",
  AT: "Austria",
  AZ: "Azerbaijan",
  BS: "Bahamas",
  BH: "Bahrain",
  BD: "Bangladesh",
  BB: "Barbados",
  BY: "Belarus",
  BE: "Belgium",
  BZ: "Belize",
  BJ: "Benin",
  BM: "Bermuda",
  BT: "Bhutan",
  BO: "Bolivia",
  BA: "Bosnia and Herzegovina",
  BW: "Botswana",
  BV: "Bouvet Island",
  BR: "Brazil",
  IO: "British Indian Ocean Territory",
  BN: "Brunei Darussalam",
  BG: "Bulgaria",
  BF: "Burkina Faso",
  BI: "Burundi",
  KH: "Cambodia",
  CM: "Cameroon",
  CA: "Canada",
  CV: "Cape Verde",
  KY: "Cayman Islands",
  CF: "Central African Republic",
  TD: "Chad",
  CL: "Chile",
  CN: "China",
  CX: "Christmas Island",
  CC: "Cocos (Keeling) Islands",
  CO: "Colombia",
  KM: "Comoros",
  CG: "Congo",
  CD: "Congo, Democratic Republic of the",
  CK: "Cook Islands",
  CR: "Costa Rica",
  CI: "Cote D'Ivoire",
  HR: "Croatia",
  CU: "Cuba",
  CY: "Cyprus",
  CZ: "Czech Republic",
  DK: "Denmark",
  DJ: "Djibouti",
  DM: "Dominica",
  DO: "Dominican Republic",
  EC: "Ecuador",
  EG: "Egypt",
  SV: "El Salvador",
  GQ: "Equatorial Guinea",
  ER: "Eritrea",
  EE: "Estonia",
  ET: "Ethiopia",
  FK: "Falkland Islands (Malvinas)",
  FO: "Faroe Islands",
  FJ: "Fiji",
  FI: "Finland",
  FR: "France",
  GF: "French Guiana",
  PF: "French Polynesia",
  TF: "French Southern Territories",
  GA: "Gabon",
  GM: "Gambia",
  GE: "Georgia",
  DE: "Germany",
  GH: "Ghana",
  GI: "Gibraltar",
  GR: "Greece",
  GL: "Greenland",
  GD: "Grenada",
  GP: "Guadeloupe",
  GU: "Guam",
  GT: "Guatemala",
  GN: "Guinea",
  GW: "Guinea-Bissau",
  GY: "Guyana",
  HT: "Haiti",
  HM: "Heard Island and Mcdonald Islands",
  VA: "Holy See (Vatican City State)",
  HN: "Honduras",
  HK: "Hong Kong",
  HU: "Hungary",
  IS: "Iceland",
  IN: "India",
  ID: "Indonesia",
  IR: "Iran, Islamic Republic Of",
  IQ: "Iraq",
  IE: "Ireland",
  IL: "Israel",
  IT: "Italy",
  JM: "Jamaica",
  JP: "Japan",
  JO: "Jordan",
  KZ: "Kazakhstan",
  KE: "Kenya",
  KI: "Kiribati",
  KP: "Korea, Democratic People's Republic of",
  KR: "Korea, Republic of",
  KW: "Kuwait",
  KG: "Kyrgyzstan",
  LA: "Lao People's Democratic Republic",
  LV: "Latvia",
  LB: "Lebanon",
  LS: "Lesotho",
  LR: "Liberia",
  LY: "Libyan Arab Jamahiriya",
  LI: "Liechtenstein",
  LT: "Lithuania",
  LU: "Luxembourg",
  MO: "Macao",
  MK: "Macedonia, The Former Yugoslav Republic of",
  MG: "Madagascar",
  MW: "Malawi",
  MY: "Malaysia",
  MV: "Maldives",
  ML: "Mali",
  MT: "Malta",
  MH: "Marshall Islands",
  MQ: "Martinique",
  MR: "Mauritania",
  MU: "Mauritius",
  YT: "Mayotte",
  MX: "Mexico",
  FM: "Micronesia, Federated States of",
  MD: "Moldova, Republic of",
  MC: "Monaco",
  MN: "Mongolia",
  MS: "Montserrat",
  MA: "Morocco",
  MZ: "Mozambique",
  MM: "Myanmar",
  NA: "Namibia",
  NR: "Nauru",
  NP: "Nepal",
  NL: "Netherlands",
  NC: "New Caledonia",
  NZ: "New Zealand",
  NI: "Nicaragua",
  NE: "Niger",
  NG: "Nigeria",
  NU: "Niue",
  NF: "Norfolk Island",
  MP: "Northern Mariana Islands",
  NO: "Norway",
  OM: "Oman",
  PK: "Pakistan",
  PW: "Palau",
  PS: "Palestinian Territory, Occupied",
  PA: "Panama",
  PG: "Papua New Guinea",
  PY: "Paraguay",
  PE: "Peru",
  PH: "Philippines",
  PN: "Pitcairn",
  PL: "Poland",
  PT: "Portugal",
  PR: "Puerto Rico",
  QA: "Qatar",
  RE: "Reunion",
  RO: "Romania",
  RU: "Russian Federation",
  RW: "Rwanda",
  SH: "Saint Helena",
  KN: "Saint Kitts and Nevis",
  LC: "Saint Lucia",
  PM: "Saint Pierre and Miquelon",
  VC: "Saint Vincent and the Grenadines",
  WS: "Samoa",
  SM: "San Marino",
  ST: "Sao Tome and Principe",
  SA: "Saudi Arabia",
  SN: "Senegal",
  CS: "Serbia and Montenegro",
  SC: "Seychelles",
  SL: "Sierra Leone",
  SG: "Singapore",
  SK: "Slovakia",
  SI: "Slovenia",
  SB: "Solomon Islands",
  SO: "Somalia",
  ZA: "South Africa",
  GS: "South Georgia and the South Sandwich Islands",
  ES: "Spain",
  LK: "Sri Lanka",
  SD: "Sudan",
  SR: "Suriname",
  SJ: "Svalbard and Jan Mayen",
  SZ: "Swaziland",
  SE: "Sweden",
  CH: "Switzerland",
  SY: "Syrian Arab Republic",
  TW: "Taiwan",
  TJ: "Tajikistan",
  TZ: "Tanzania, United Republic of",
  TH: "Thailand",
  TL: "Timor-Leste",
  TG: "Togo",
  TK: "Tokelau",
  TO: "Tonga",
  TT: "Trinidad and Tobago",
  TN: "Tunisia",
  TR: "Turkey",
  TM: "Turkmenistan",
  TC: "Turks and Caicos Islands",
  TV: "Tuvalu",
  UG: "Uganda",
  UA: "Ukraine",
  AE: "United Arab Emirates",
  GB: "United Kingdom",
  US: "United States",
  UM: "United States Minor Outlying Islands",
  UY: "Uruguay",
  UZ: "Uzbekistan",
  VU: "Vanuatu",
  VE: "Venezuela",
  VN: "Vietnam",
  VG: "Virgin Islands, British",
  VI: "Virgin Islands, U.S.",
  WF: "Wallis and Futuna",
  EH: "Western Sahara",
  YE: "Yemen",
  ZM: "Zambia",
  ZW: "Zimbabwe",
};

type TimePeriod = "24h" | "7d" | "30d" | "6mo" | "12mo";

export default function AnalyticsPage() {
  const { data: session } = useSession();
  const userSlug = session?.user?.name?.toLowerCase() || "username";
  const [timePeriod, setTimePeriod] = useState<TimePeriod>("30d");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const [analyticsData, setAnalyticsData] = useState<{
    totalClicks: number;
    todayClicks: number;
    topCountries: any[];
    devices: Device[];
    browsers: any[];
    peakHours: any[];
    referrers: any[];
    fullLink: string;
    totalVisitors: number;
    bounceRate: number;
    visitDuration: number;
  }>({
    totalClicks: 0,
    todayClicks: 0,
    topCountries: [],
    devices: [],
    browsers: [],
    peakHours: [],
    referrers: [],
    fullLink: `https://emogir.ls/@${userSlug}`,
    totalVisitors: 0,
    bounceRate: 0,
    visitDuration: 0,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`/api/analytics?period=${timePeriod}`);
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to fetch analytics");
        }

        const { aggregate, browsers, devices, locations, sources, timeseries } =
          data;

        setAnalyticsData({
          totalClicks: aggregate.results.pageviews.value,
          todayClicks:
            timeseries.results[timeseries.results.length - 1].visitors,
          topCountries: locations.results
            .map((country: any) => ({
              code: country.country || "Unknown",
              name:
                COUNTRY_NAMES[country.country] || country.country || "Unknown",
              visits: country.visitors,
            }))
            .slice(0, 10),
          devices: devices.results.map((device: any) => ({
            type: device.device || "Unknown",
            percentage: Math.round(
              (device.visitors / aggregate.results.visitors.value) * 100,
            ),
          })),
          browsers: browsers.results.map((browser: any) => ({
            name: browser.browser || "Unknown",
            percentage: Math.round(
              (browser.visitors / aggregate.results.visitors.value) * 100,
            ),
          })),
          peakHours: timeseries.results
            .filter((hour: any) => new Date(hour.date) <= new Date())
            .map((hour: any) => ({
              hour: new Date(hour.date).toLocaleTimeString([], {
                hour: "2-digit",
                hour12: false,
              }),
              clicks: hour.visitors,
            })),
          referrers: sources.results.map((source: any) => ({
            name: source.source || "Direct",
            url: source.source || "Direct",
            visits: source.visitors,
            iconUrl: null,
          })),
          fullLink: `https://emogir.ls/@${userSlug}`,
          totalVisitors: aggregate.results.visitors.value,
          bounceRate: aggregate.results.bounce_rate?.value || 0,
          visitDuration: aggregate.results.visit_duration?.value || 0,
        });
      } catch (error) {
        console.error("Error fetching analytics:", error);
        toast({
          title: "Error",
          description: "Failed to load analytics data",
          variant: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userSlug, timePeriod]);

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast({
        title: "Success",
        description: "URL copied to clipboard!",
        variant: "success",
      });
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to copy URL",
        variant: "error",
      });
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <div className="flex items-center gap-4">
            <Skeleton className="h-10 w-[180px]" />
            <Skeleton className="h-10 w-[300px]" />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="p-6 rounded-lg border border-primary/[0.125] bg-gradient-to-tr from-darker/80 to-darker/60"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-3">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-16" />
                  <Skeleton className="h-3 w-20" />
                </div>
                <Skeleton className="h-8 w-8 rounded-full" />
              </div>
            </div>
          ))}
        </div>

        <div className="grid gap-6">
          <div className="rounded-lg border border-primary/[0.125] bg-gradient-to-tr from-darker/80 to-darker/60 p-6">
            <div className="flex items-center justify-between mb-4">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-6 w-6 rounded-full" />
            </div>
            <Skeleton className="h-[300px] w-full" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="rounded-lg border border-primary/[0.125] bg-gradient-to-tr from-darker/80 to-darker/60 p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <Skeleton className="h-6 w-32" />
                  <Skeleton className="h-6 w-6 rounded-full" />
                </div>
                <div className="space-y-4">
                  {[...Array(5)].map((_, j) => (
                    <div key={j} className="flex justify-between items-center">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-4 w-16" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>

        <div className="flex items-center gap-4">
          <Select
            value={timePeriod}
            onValueChange={(value: TimePeriod) => setTimePeriod(value)}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select time period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="6mo">Last 6 months</SelectItem>
              <SelectItem value="12mo">Last 12 months</SelectItem>
            </SelectContent>
          </Select>

          <button
            onClick={() => copyToClipboard(analyticsData.fullLink)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-primary/[0.125] bg-gradient-to-tr from-darker/80 to-darker/60 hover:border-primary/20 transition-all group"
          >
            <span className="text-sm text-white/70 font-medium">
              {analyticsData.fullLink}
            </span>
            <IconCopy size={14} className="text-primary transition-colors" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Clicks"
          value={analyticsData.totalClicks.toLocaleString()}
          icon={IconClick}
          subLabel="Overall"
        />
        <StatCard
          title="Bounce Rate"
          value={`${Math.round(analyticsData.bounceRate)}%`}
          icon={IconArrowUpRight}
          subLabel="Average"
        />
        <StatCard
          title="Avg. Visit Duration"
          value={`${Math.round(analyticsData.visitDuration / 60)}m`}
          icon={IconClock}
          subLabel="Per session"
        />
        <StatCard
          title="Unique Visitors"
          value={analyticsData.totalVisitors.toLocaleString()}
          icon={IconUsers}
          subLabel="This month"
          subValue={<span className="text-primary">+24.5%</span>}
        />
      </div>

      <div className="grid gap-6">
        <DataCard title="Traffic Overview" icon={IconChartBar}>
          <div className="px-4">
            <AnalyticsGraph
              data={analyticsData.peakHours.map((h) => ({
                label: h.hour,
                value: h.clicks,
              }))}
            />
          </div>
        </DataCard>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <DataCard title="Device Distribution" icon={IconDeviceLaptop}>
            <div className="p-4">
              {analyticsData.devices.map((device) => (
                <div key={device.type} className="mb-4 last:mb-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium">{device.type}</span>
                    <span className="text-xs text-white/60">
                      {device.percentage}%
                    </span>
                  </div>
                  <div className="h-1 bg-primary/10 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#ff3379] transition-all"
                      style={{ width: `${device.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </DataCard>

          <DataCard title="Top Referrers" icon={IconLink}>
            <div className="-mx-3 divide-y divide-primary/5">
              {analyticsData.referrers.map((referrer) => (
                <div
                  key={referrer.name}
                  className="group flex items-center justify-between py-2 px-3 hover:bg-primary/5"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {referrer.iconUrl ? (
                      <img
                        src={referrer.iconUrl}
                        alt={referrer.name}
                        className="w-4 h-4 flex-shrink-0"
                      />
                    ) : (
                      <div className="w-4 h-4 rounded bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <IconLink size={12} className="text-primary" />
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm truncate">{referrer.name}</p>
                      {referrer.url && (
                        <p className="text-xs text-white/40 truncate">
                          {referrer.url}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 pl-3">
                    <span className="text-xs text-white/60">
                      {referrer.visits.toLocaleString()}
                    </span>
                    <IconArrowUpRight
                      size={14}
                      className="opacity-0 group-hover:opacity-60 transition-opacity"
                    />
                  </div>
                </div>
              ))}
            </div>
          </DataCard>

          <DataCard title="Browser Share" icon={IconBrowser}>
            <div className="-mx-3 divide-y divide-primary/5">
              {analyticsData.browsers.map((browser) => (
                <div
                  key={browser.name}
                  className="flex items-center justify-between py-2 px-3 hover:bg-primary/5"
                >
                  <div className="flex items-center gap-2">
                    <IconBrowser size={14} className="text-white/60" />
                    <span className="text-sm">{browser.name}</span>
                  </div>
                  <span className="text-xs text-white/60">
                    {browser.percentage}%
                  </span>
                </div>
              ))}
            </div>
          </DataCard>

          <DataCard title="Geographic Distribution" icon={IconWorld}>
            <div className="-mx-3 divide-y divide-primary/5">
              {analyticsData.topCountries.map((country) => (
                <div
                  key={country.code}
                  className="flex items-center justify-between py-2 px-3 hover:bg-primary/5"
                >
                  <div className="flex items-center gap-2">
                    <IconWorld size={14} className="text-white/60" />
                    <span className="text-sm">
                      {country.name} ({country.code})
                    </span>
                  </div>
                  <span className="text-xs text-white/60">
                    {country.visits.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </DataCard>
        </div>
      </div>
    </div>
  );
}
