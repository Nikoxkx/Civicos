/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    "intro",
    {
      type: "category",
      label: "Getting Started",
      items: ["getting-started/installation", "getting-started/quickstart", "getting-started/first-ingestion"],
    },
    {
      type: "category",
      label: "Architecture",
      items: ["architecture/overview", "architecture/extraction-pipeline", "architecture/database-schema"],
    },
    {
      type: "category",
      label: "API Reference",
      items: ["api/overview", "api/programs", "api/cities", "api/categories", "api/search", "api/admin"],
    },
    {
      type: "category",
      label: "Guides",
      items: ["guides/adding-a-city", "guides/deploying", "guides/contributing"],
    },
  ],
};

module.exports = sidebars;