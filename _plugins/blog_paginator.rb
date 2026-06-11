# frozen_string_literal: true

# =============================================================================
# Server-side pagination for the Best-of-the-Best daily blog.
#
# The daily posts live as *pages* under blog/posts/*.md (not _posts), so the
# classic jekyll-paginate plugin cannot touch them — it only iterates
# site.posts. This generator collects those pages, sorts them newest-first,
# and splits them into fixed-size pages:
#
#   page 1 -> /blog/         (the existing, already-indexed blog/index.html)
#   page N -> /blog/pageN/   (generated here)
#
# Each output page renders the same listing include and carries its own
# canonical URL plus a `pg` paginator object consumed by
# _includes/blog-archive-list.html.
#
# Runs during `bundle exec jekyll build` (the deploy workflow does NOT use
# --safe), so this plugin executes in production.
# =============================================================================

module BestOfTheBest
  class BlogPaginator < Jekyll::Generator
    safe true
    priority :low

    PER_PAGE = 7

    def generate(site)
      posts = site.pages.select do |p|
        p.path.start_with?("blog/posts/") && p.data["date"]
      end
      return if posts.empty?

      posts = posts.sort_by { |p| p.data["date"] }.reverse

      total_posts = posts.size
      total_pages = (total_posts.to_f / PER_PAGE).ceil

      index_page = site.pages.find { |p| p.path == "blog/index.html" }

      (1..total_pages).each do |num|
        slice = posts[(num - 1) * PER_PAGE, PER_PAGE] || []
        start_index = ((num - 1) * PER_PAGE) + 1
        end_index = start_index + slice.size - 1

        pg = {
          "page"        => num,
          "total_pages" => total_pages,
          "total_posts" => total_posts,
          "start_index" => start_index,
          "end_index"   => end_index,
          "per_page"    => PER_PAGE,
        }

        if num == 1
          next unless index_page

          index_page.data["paginated_posts"] = slice
          index_page.data["pg"] = pg
        else
          site.pages << build_page(site, num, slice, pg)
        end
      end
    end

    private

    def build_page(site, num, slice, pg)
      page = Jekyll::PageWithoutAFile.new(site, site.source, "blog/page#{num}", "index.html")
      page.content = "{% include blog-archive-list.html %}"
      page.data.merge!(
        "layout"          => "archive",
        "permalink"       => "/blog/page#{num}/",
        "title"           => "Best-of-the-Best Blog",
        "description"     => "Daily AI technology intelligence — rankings, summaries, and implementation notes on emerging AI packages, papers, and open-source repositories. Page #{num} of #{pg["total_pages"]}.",
        "author_profile"  => true,
        "sitemap"         => true,
        "classes"         => [],
        "header"          => {
          "overlay_filter"       => "0.6",
          "overlay_image"        => "/assets/images/header-blog.jpg",
          "show_overlay_excerpt" => false,
        },
        "paginated_posts" => slice,
        "pg"              => pg,
      )
      page
    end
  end
end
