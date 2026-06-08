// @ts-check
/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "CivicOS",
  tagline: "Open-source civic data intelligence platform",
  favicon: "favicon.ico",
  url: "https://civicos.dev",
  baseUrl: "/",
  organizationName: "Yeisbel",
  projectName: "civicos",
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",

  presets: [
    [
      "classic",
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve("./sidebars.js"),
          editUrl: "https://github.com/Yeisbel/civicos/tree/main/docs/",
        },
        theme: { customCss: require.resolve("./src/css/custom.css") },
      }),
    ],
  ],

  themeConfig: /** @type {import('@docusaurus/preset-classic').ThemeConfig} */ ({
    colorMode: { defaultMode: "dark", respectPrefersColorScheme: true },
    navbar: {
      title: "CivicOS",
      items: [
        { to: "/docs/intro", label: "Docs", position: "left" },
        { to: "/docs/api/overview", label: "API", position: "left" },
        { href: "https://github.com/Yeisbel/civicos", label: "GitHub", position: "right" },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Docs",
          items: [
            { label: "Getting Started", to: "/docs/intro" },
            { label: "API Reference", to: "/docs/api/overview" },
            { label: "Architecture", to: "/docs/architecture/overview" },
          ],
        },
        {
          title: "Community",
          items: [
            { label: "GitHub", href: "https://github.com/Yeisbel/civicos" },
            { label: "Issues", href: "https://github.com/Yeisbel/civicos/issues" },
          ],
        },
      ],
      copyright: `Built with ❤️ in Dorchester, Boston. MIT Licensed.`,
    },
  }),
};

module.exports = config;