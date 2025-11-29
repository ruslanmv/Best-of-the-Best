source "https://rubygems.org"

# Your system Ruby is 3.0.x (Ubuntu 22.04)
ruby "~> 3.0"

# Core Jekyll + theme
gem "jekyll", "~> 4.3.4"
gem "minimal-mistakes-jekyll", "~> 4.27.3"

# ---- Compatibility pins ----
gem "addressable", "~> 2.8.6"
gem "public_suffix", "< 6.0"

group :jekyll_plugins do
  # Standard plugins
  gem "jekyll-feed",    "~> 0.17"
  gem "jekyll-sitemap", "~> 1.4"
  
  # Recommended by Minimal Mistakes
  gem "jekyll-include-cache", "~> 0.2"

  # Use the older sassc-based converter
  gem "jekyll-sass-converter", "~> 2.2"

  # --- MISSING GEMS ADDED BELOW ---
  gem "gemoji"            # Fixes your current error
  gem "jekyll-paginate"   # Required by your _config.yml
  gem "jekyll-gist"       # Required by your _config.yml
end

# Needed to run `bundle exec jekyll serve` on Ruby 3.x
gem "webrick", "~> 1.8"

# Timezone data for Windows / JRuby
gem "tzinfo-data", platforms: %i[mingw mswin x64_mingw jruby]

# For Faraday v2 retry middleware
gem "faraday-retry"