You can read the script doc comment but also see from the conversation generating the script:

Task complete 
  └ Done. index.html now has the sweeper data active, and the previous embedded payload is preserved in a comment labelled Thursday 30th April.

    The new swap utility is scripts/swap_embedded_data.py:

     1. python3 scripts/swap_embedded_data.py apply --source-dir ~/projects/jameel-institute/sweeper
     2. python3 scripts/swap_embedded_data.py restore

    I split the work into atomic commits:

     1. 87070a5 — Handle sparse embedded datasets
     2. 5281a45 — Add embedded data swap script
     3. 66e9e6a — Import sweeper embedded data

    Breakage assessment: the HTML should not break with the current sweeper repo. The country, capacity, and response dropdowns are data-driven. What was brittle before was the hard-coded startup selection and always-on heatmap view; that is now
    fixed. Missing tiers are simply absent from the UI, and the heatmap is hidden for countries with fewer than 2 tiers.

    One useful nuance: the sweeper directory is currently partially complete, not just default-only. It has default tiers for all 10 countries and max tiers for 6 of them (brn, idn, khm, lao, mmr, mys), with no mid tiers present. The page now
    handles that partial coverage safely.
▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
 ❯ Note that the sweeper repo is continually being updated with more data. Is there an easy way to programmatically grab the new data and overwrite the existing data grab from sweeper, without doing the comment-it-out thing?                     
▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
● Yes. On the current index.html, just rerun:

   python3 scripts/swap_embedded_data.py apply --source-dir ~/projects/jameel-institute/sweeper

  Because the original archive comment is already there, apply now just replaces the active imported dataset block and import metadata in place. It does not add another commented-out copy each time.

  The only time it does the comment/archive step is the first apply against an HTML file that has no archive yet.
