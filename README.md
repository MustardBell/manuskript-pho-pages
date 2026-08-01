# PHO Pages for Manuskript

[![Tests](https://github.com/MustardBell/manuskript-pho-pages/actions/workflows/tests.yml/badge.svg)](https://github.com/MustardBell/manuskript-pho-pages/actions/workflows/tests.yml)

PHO Pages is a plugin for [MustardBell's Manuskript fork](https://github.com/MustardBell/manuskript). It turns structured Parahumans Online source text into an editable PHO page with a rendered reading view, a form-based wizard, and format-aware compile output.

The plugin requires Manuskript Plugin API 1, which is currently provided by the `develop` branch of that fork. It does not work with the original [`olivierkes/manuskript`](https://github.com/olivierkes/manuskript), which does not provide this plugin API.

## What it provides

- A per-page **PHO page** property instead of a global editor mode.
- A full rendered reading view for PHO pages.
- A structured wizard in place of live Markdown preview.
- A format-neutral PHO model separated from its parser, wizard, and renderers.
- Portable Markdown output for ordinary HTML, LaTeX, e-book, and other compile pipelines.
- Direct forum BBCode output, including neutralized `@` mentions.
- Configurable content, labels, separators, date presentation, pagination, and output templates.
- Raw source that remains ordinary editable text when the plugin is disabled or removed.

## Install into a source checkout

Clone the plugin as one subdirectory of Manuskript's plugin root. The destination directory is intentionally named `pho_pages`; the Git repository remains independent from Manuskript.

```bash
cd /path/to/manuskript
git clone https://github.com/MustardBell/manuskript-pho-pages.git manuskript/plugins/pho_pages
```

If you deliberately track plugins as submodules in your own Manuskript checkout, use:

```bash
cd /path/to/manuskript
git submodule add https://github.com/MustardBell/manuskript-pho-pages.git manuskript/plugins/pho_pages
```

Do not run both commands for the same checkout.

## Install into another build of the fork

Open **Tools → Plugins → Manage Plugins…** and note the plugin root shown at the top of the dialog. Close Manuskript, then clone this repository into a `pho_pages` subdirectory of that exact root.

```bash
git clone https://github.com/MustardBell/manuskript-pho-pages.git /path/shown/by/manuskript/pho_pages
```

The current host discovers plugins only under the directory shown in the manager. If a packaged installation makes that directory read-only, use a source checkout until the fork gains a per-user plugin installer.

## Enable and use

1. Start Manuskript, or select **Refresh** in **Tools → Plugins → Manage Plugins…** after installing the plugin.
2. Select **PHO Pages**, choose **Enable**, and confirm the trust warning.
3. Select a Markdown page and enable **PHO page** in its Properties panel.
   - An empty page is initialized as a valid PHO page.
   - Existing body text produces a warning before activation; it is interpreted as the original post and is not rewritten until changes are applied in the wizard.
4. Use **Reading** for the complete rendered page and **Live Preview** for the structured PHO wizard.
5. Configure renderer routing and templates from the PHO Pages entry in the plugin manager.

The plugin is executable Python code and runs with the same filesystem access as Manuskript. Review and enable only versions you trust.

## Update or remove

Update the independent checkout, then restart Manuskript or refresh the plugin manager:

```bash
git -C /path/to/manuskript/manuskript/plugins/pho_pages pull --ff-only
```

To remove it, disable **PHO Pages**, close Manuskript, and remove the plugin directory. PHO source remains in the project as editable raw text.

## Background

The source format and PHO conversion behavior were developed for [Manuskript Worm Wordsmith](https://github.com/MustardBell/manusrkript-worm-wordsmith). This plugin is a Python implementation built around the fork's page-type, presentation, wizard, and compile extension points rather than a wrapper around the browser-based converter.

## Development

The plugin is intentionally split by responsibility:

- `model.py` parses and serializes the portable source format.
- `presentation.py` resolves it into a format-neutral semantic model.
- `renderer.py` owns the full reading projection.
- `export_renderers.py` owns Markdown and BBCode output.
- `wizard_view.py`, `wizard_controller.py`, and `wizard.py` implement the editor without coupling the view to source mutation.
- `plugin.py` contains only host registration and configurable renderer fields.

Run the plugin integration suite from a compatible Manuskript checkout:

```bash
cd /path/to/manuskript
python3 -B -m pytest -q manuskript/plugins/pho_pages/tests
```

## License

PHO Pages is distributed under the GNU General Public License, version 3 or, at your option, any later version. See `LICENSE`.
