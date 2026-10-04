/**
 * TEMPORARY DEVELOPMENT FIXTURES ONLY
 * 
 * Notice: The movies and recommendation vectors in this file are temporary
 * static fixtures designed strictly for Phase 2B frontend UI/UX verification.
 * They do NOT represent real machine learning recommendation-model outputs,
 * live TMDB API responses, or MovieLens database records.
 */

import type { Movie, RecommendationRowData } from '../types/movie';

export const HERO_MOVIE: Movie = {
  id: 'blade-runner-2049',
  title: 'BLADE RUNNER 2049',
  year: 2017,
  director: 'Denis Villeneuve',
  runtime: '2h 44m',
  certificate: 'R',
  rating: 4.8,
  matchScore: 96,
  matchBadgeText: 'POPULAR',
  matchReason: 'BECAUSE OF WORLD-BUILDING, PHILOSOPHICAL SCALE & ZIMMER SCORE',
  genres: ['Sci-Fi', 'Neo-Noir', 'Cyberpunk', 'Mystery'],
  tags: ['Auteur Vision', 'Atmospheric Dread', 'Roger Deakins Lighting', 'Dystopian Solitude'],
  formats: ['IMAX Enhanced', 'Dolby Atmos'],
  overview:
    'Thirty years after the events of the first film, a new blade runner, LAPD Officer K, unearths a long-buried secret that has the potential to plunge what’s left of society into chaos.',
  poster:
    'https://lh3.googleusercontent.com/aida-public/AB6AXuAgLAY387AM5S_6DkFqt3VJiCCsNaxUTlq17_UkodeMUF8TarhH7MEB_RgYAPJVREGdGIv1fGtmht2YGQuLqwVCZ8RpJYzElXQEK0HIX0tdUstseU792g-TZWAscqvmk_f_LH1t1yvrJa5rftEzx7aWN0QPR0iXwsfqN4qsJ7zre7gX4OFmzryh80bNIbcEHyNxjL1HRKbaTo-nE47Y-HGCAyj5aL81GQinQRzzo2FW20GMJevBnxiB',
  backdrop:
    'https://lh3.googleusercontent.com/aida-public/AB6AXuAgLAY387AM5S_6DkFqt3VJiCCsNaxUTlq17_UkodeMUF8TarhH7MEB_RgYAPJVREGdGIv1fGtmht2YGQuLqwVCZ8RpJYzElXQEK0HIX0tdUstseU792g-TZWAscqvmk_f_LH1t1yvrJa5rftEzx7aWN0QPR0iXwsfqN4qsJ7zre7gX4OFmzryh80bNIbcEHyNxjL1HRKbaTo-nE47Y-HGCAyj5aL81GQinQRzzo2FW20GMJevBnxiB',
  explainability: {
    directorAffinity: 98,
    thematicFit: 96,
    audiovisualScore: 95,
    naturalLanguageReason:
      'High correlation with your logged preference for slow-burn existential science fiction, monolithic architecture, and dense synth sound design.',
  },
};

export const MOCK_RECOMMENDATION_ROWS: RecommendationRowData[] = [
  {
    id: 'row-interstellar',
    title: 'Because you liked Interstellar',
    subtitle: 'Films sharing cosmic existentialism, temporal relativity, and deep emotional stakes.',
    anchorBadge: 'Explainable Anchor • Christopher Nolan Cluster',
    iconType: 'hub',
    movies: [
      {
        id: 'arrival',
        title: 'Arrival',
        year: 2016,
        director: 'Denis Villeneuve',
        runtime: '1h 56m',
        rating: 4.7,
        matchScore: 97,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Drama', 'Mystery'],
        tags: ['Non-linear Time', 'Linguistics'],
        overview:
          'Linguist Louise Banks leads an elite team when mysterious spacecraft touch down across the globe.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCtUE9W8HL9lqFvgQJtHOCkn0jaTOmAhdAKcHfc9Rsbgkdg9l7PGeNQUkcold3qXI6UY_1ymoI5L4bHJDpmIWtv1bxiVv6fHHn7GUU5YjQWKUlsVxsQCcjiAaPMQagSn85UaDGtma_4pJt9A9v17wUHdQe-aFBZKWOHnjOxs1Jw13bLXkhPOKNTTcvzmeCuCAdX_nIgGrHmfOanHNA0VNWrv1LAegimQyLZ9-FVDIzcs6L-kWPsAK6T',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCtUE9W8HL9lqFvgQJtHOCkn0jaTOmAhdAKcHfc9Rsbgkdg9l7PGeNQUkcold3qXI6UY_1ymoI5L4bHJDpmIWtv1bxiVv6fHHn7GUU5YjQWKUlsVxsQCcjiAaPMQagSn85UaDGtma_4pJt9A9v17wUHdQe-aFBZKWOHnjOxs1Jw13bLXkhPOKNTTcvzmeCuCAdX_nIgGrHmfOanHNA0VNWrv1LAegimQyLZ9-FVDIzcs6L-kWPsAK6T',
      },
      {
        id: 'contact',
        title: 'Contact',
        year: 1997,
        director: 'Robert Zemeckis',
        runtime: '2h 30m',
        rating: 4.5,
        matchScore: 94,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Drama', 'Mystery'],
        tags: ['Scientific Faith', 'Signal Theory'],
        overview:
          'Dr. Ellie Arroway discovers the first conclusive extraterrestrial radio transmission from Vega.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAV_tBr0IE3HdRryvi4M_6cz2Gw2GkOOSQFKvCIpB7x70OPZ03BV1B3gS013kL6rnAxcZI8DaoCq8VGx83--JiycXT2P-5B7sdipN1BCF9lnoQ705mU4-8oLcSSialicfKel0CpNNDC67O0-LoaVHmn_s7PIhMgclgerxM8qit1B6XGdnb_yzYYZIWruA-kz6tXPLF5CfeGKzU85fb-t1bebKT-DO4xFfA2NlkJ12UPM2qfTWaHyGSh',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAV_tBr0IE3HdRryvi4M_6cz2Gw2GkOOSQFKvCIpB7x70OPZ03BV1B3gS013kL6rnAxcZI8DaoCq8VGx83--JiycXT2P-5B7sdipN1BCF9lnoQ705mU4-8oLcSSialicfKel0CpNNDC67O0-LoaVHmn_s7PIhMgclgerxM8qit1B6XGdnb_yzYYZIWruA-kz6tXPLF5CfeGKzU85fb-t1bebKT-DO4xFfA2NlkJ12UPM2qfTWaHyGSh',
      },
      {
        id: '2001-a-space-odyssey',
        title: '2001: A Space Odyssey',
        year: 1968,
        director: 'Stanley Kubrick',
        runtime: '2h 29m',
        rating: 4.9,
        matchScore: 95,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Adventure', 'Mystery'],
        tags: ['Human Evolution', 'Cosmic Canon'],
        overview:
          'After uncovering a mysterious artifact on the Moon, humanity embarks on a voyage toward Jupiter.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAsjN2fQRncwwTfNsTNukg1rGh3PJ0CQnWv3qWONtKkimVqSbfvN1EcMQViG3qxfOHUKiVR8wDkLx1HwUlv5uzg2WoDgRpQAz7EFJhJpHWVYDGOtbT9bd-i-I-LPZxKu5hpWasL6z-1i2_w0DayEi3gwEe1NgUJhhH4DT21D3krM7aZJKqLZgxMw3eOPXhDNxTmJ7ssZoY02KGegNnKRszxO6e40q8jSOfU68vV5apvgDd3JtW1EJWh',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAsjN2fQRncwwTfNsTNukg1rGh3PJ0CQnWv3qWONtKkimVqSbfvN1EcMQViG3qxfOHUKiVR8wDkLx1HwUlv5uzg2WoDgRpQAz7EFJhJpHWVYDGOtbT9bd-i-I-LPZxKu5hpWasL6z-1i2_w0DayEi3gwEe1NgUJhhH4DT21D3krM7aZJKqLZgxMw3eOPXhDNxTmJ7ssZoY02KGegNnKRszxO6e40q8jSOfU68vV5apvgDd3JtW1EJWh',
      },
      {
        id: 'solaris',
        title: 'Solaris',
        year: 1972,
        director: 'Andrei Tarkovsky',
        runtime: '2h 47m',
        rating: 4.7,
        matchScore: 92,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Drama', 'Mystery'],
        tags: ['Grief & Cosmos', 'Poetic Memory'],
        overview:
          'A psychologist is sent to a station orbiting a distant planet whose sentient ocean manifests past regrets.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDDyfU-LP-aMha8Stf4FKzzSO7mobIlhZGHsSKc2Wwlz6x1yQ_Ja3QVzgsBoJLFFlgvjLvtGdVTE4WaBypp67hZ4Q6OSLATOcAk-Lrt-dAdwf8qRnph2HEGadHh5eTjmXEfHZWFv7vfNXxTqVU4ganZKYXKuY17Rk6AtRzZTvphKB25uxhAnOeumRKGkaymUdWiEELPjX68stnfH8aPEn07KaEiG0xtDe6gxOCrtZ-hDtgEyPamrGna',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDDyfU-LP-aMha8Stf4FKzzSO7mobIlhZGHsSKc2Wwlz6x1yQ_Ja3QVzgsBoJLFFlgvjLvtGdVTE4WaBypp67hZ4Q6OSLATOcAk-Lrt-dAdwf8qRnph2HEGadHh5eTjmXEfHZWFv7vfNXxTqVU4ganZKYXKuY17Rk6AtRzZTvphKB25uxhAnOeumRKGkaymUdWiEELPjX68stnfH8aPEn07KaEiG0xtDe6gxOCrtZ-hDtgEyPamrGna',
      },
      {
        id: 'the-martian',
        title: 'The Martian',
        year: 2015,
        director: 'Ridley Scott',
        runtime: '2h 24m',
        rating: 4.6,
        matchScore: 91,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Adventure', 'Drama'],
        tags: ['Ingenuity', 'Procedural Grit'],
        overview:
          'An astronaut becomes stranded on Mars after his crew assumes him dead and must rely on his ingenuity.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAuD_N94O90YgfZUKrtP0RePKHuKg2ulQeoXbKGjJwElIR-odmIC2oKAVNQvK-F1g7Z5qAkm071U6pXyX-x4Rh-VVrjvFf1fD7e3O91SaQg4La5Ezi5SuAI_ajsmHLw3NDucGEDOWmA9jA_GwAP_dOE4WRt-1q9IMSPjJNVabZcEQ-OjGUZpxQ4TnK0uxpPdxPsyrl7JxRPRqDKhQe9kOk0flJ91Ag-zvb32hc6-wFasSuIHtpk6tM6',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAuD_N94O90YgfZUKrtP0RePKHuKg2ulQeoXbKGjJwElIR-odmIC2oKAVNQvK-F1g7Z5qAkm071U6pXyX-x4Rh-VVrjvFf1fD7e3O91SaQg4La5Ezi5SuAI_ajsmHLw3NDucGEDOWmA9jA_GwAP_dOE4WRt-1q9IMSPjJNVabZcEQ-OjGUZpxQ4TnK0uxpPdxPsyrl7JxRPRqDKhQe9kOk0flJ91Ag-zvb32hc6-wFasSuIHtpk6tM6',
      },
      {
        id: 'ad-astra',
        title: 'Ad Astra',
        year: 2019,
        director: 'James Gray',
        runtime: '2h 3m',
        rating: 4.3,
        matchScore: 89,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Drama', 'Mystery'],
        tags: ['Psychological Void', 'Paternal Voyage'],
        overview:
          'Astronaut Roy McBride travels to the outer edges of the solar system to locate his missing father.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDPRsd4p_oLaFFHPTzQ1zvKp8lAUk-sf5S5qVYgaj8vwr6zBuingP0w49XEl2SzVMOEU2OaDmdCCrb3mdtStLMkDFA_Gvuxztl_8HACtm8lokf1x-6HxyiNfnAlOiCcw8_CFI9j8XjzpccR0uIpvH-S6sImHc4ybSbq5wF5O2FC1CzYlMiTaJLo-UIXTHBGb6gsLZIom1sGbNyXPLSMTPlwHOZkSFkyq1ViUPmsruiQWC0KF5Mg-v3t',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDPRsd4p_oLaFFHPTzQ1zvKp8lAUk-sf5S5qVYgaj8vwr6zBuingP0w49XEl2SzVMOEU2OaDmdCCrb3mdtStLMkDFA_Gvuxztl_8HACtm8lokf1x-6HxyiNfnAlOiCcw8_CFI9j8XjzpccR0uIpvH-S6sImHc4ybSbq5wF5O2FC1CzYlMiTaJLo-UIXTHBGb6gsLZIom1sGbNyXPLSMTPlwHOZkSFkyq1ViUPmsruiQWC0KF5Mg-v3t',
      },
    ],
  },
  {
    id: 'row-personalized',
    title: 'Personalized For You',
    subtitle: 'Deep learning recommendations based on your 142 logged ratings and aesthetic affinity vectors.',
    anchorBadge: 'Neural Taste Weighting',
    iconType: 'psychology',
    movies: [
      {
        id: 'oppenheimer',
        title: 'Oppenheimer',
        year: 2023,
        director: 'Christopher Nolan',
        runtime: '3h 0m',
        rating: 4.9,
        matchScore: 98,
        matchBadgeText: 'POPULAR',
        genres: ['Biography', 'Drama', 'History'],
        tags: ['Editing & Score', 'Tension'],
        overview:
          'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBQootNj1hyk0qu4ujkFUW8Ks6Xj547k02lIQ-NwCXbUFPLLOFCQYGXB4JRO3p0_c5Fc6TzXtMaCmlLV1IkwOu7ebStT5rly-SPw0NPt4wn7Na8EyXQKrCLaDx2lwFrRjdPpFdRmhgCG-U2BoDagDtJsY296u_ENAgmsOOm_DefvkCOz62fXITXrKvT69UqxnE9AEsnbhAQ82JBsTTy1ZYM3rKsiG-hS6WPbo-XAuBVyRQrGLUd2PYm',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBQootNj1hyk0qu4ujkFUW8Ks6Xj547k02lIQ-NwCXbUFPLLOFCQYGXB4JRO3p0_c5Fc6TzXtMaCmlLV1IkwOu7ebStT5rly-SPw0NPt4wn7Na8EyXQKrCLaDx2lwFrRjdPpFdRmhgCG-U2BoDagDtJsY296u_ENAgmsOOm_DefvkCOz62fXITXrKvT69UqxnE9AEsnbhAQ82JBsTTy1ZYM3rKsiG-hS6WPbo-XAuBVyRQrGLUd2PYm',
      },
      {
        id: 'ex-machina',
        title: 'Ex Machina',
        year: 2014,
        director: 'Alex Garland',
        runtime: '1h 48m',
        rating: 4.7,
        matchScore: 96,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Drama', 'Thriller'],
        tags: ['Chamber Sci-Fi', 'Turing Test'],
        overview:
          'A programmer is selected to participate in a ground-breaking experiment in synthetic intelligence.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBmCq2tk8IZFd_JswNbW8xWlhxYeop2OE122zbvpkFYDJdgZofwq2Zp-Z-WXkB3P-Di2HNcYV9BbRIABR5g7SzUZuA1sXJgWQ8_EeMMI2ES75Inol6Bh0yDcDNM6l4UsOpVKkjxXd9siVS8c03QeMwgc_abS8fnk8jRi8-G_IYUHMor6-ifWgJTtK2YeBe7aeTi2wdZRMPSnUf0kymFQoRw7dWn4ZujObVzzsCXU3ebTJeKdZCl-AUS',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBmCq2tk8IZFd_JswNbW8xWlhxYeop2OE122zbvpkFYDJdgZofwq2Zp-Z-WXkB3P-Di2HNcYV9BbRIABR5g7SzUZuA1sXJgWQ8_EeMMI2ES75Inol6Bh0yDcDNM6l4UsOpVKkjxXd9siVS8c03QeMwgc_abS8fnk8jRi8-G_IYUHMor6-ifWgJTtK2YeBe7aeTi2wdZRMPSnUf0kymFQoRw7dWn4ZujObVzzsCXU3ebTJeKdZCl-AUS',
      },
      {
        id: 'children-of-men',
        title: 'Children of Men',
        year: 2006,
        director: 'Alfonso Cuarón',
        runtime: '1h 49m',
        rating: 4.8,
        matchScore: 95,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Action', 'Drama'],
        tags: ['Lubezki Vision', 'Long Takes'],
        overview:
          'In 2027, in a chaotic world in which women have become inexplicably infertile, a former activist agrees to protect a miracle.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCpR2dKiOnAHH2jOqgx5xG-dc4eJDIbRRWvvSBCUP8qioHJUsjHYzS_TH88Dili94ydti0k11qbLP4nWMOGhhZ3_BBdbH6yqA6L9IK0BnOulO2AAUVfdG1QwuuXlJraFItkQtNu4COFT53V5PkznszsegmciR81kMZpqnqWPDx2PcVn9uF5IndppKWzNitFYf8Z7hdlEJZIFRpiDz83GHeY4S9HGTdLnB_N85Vb-0Lu5nacrvSFyN_J',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCpR2dKiOnAHH2jOqgx5xG-dc4eJDIbRRWvvSBCUP8qioHJUsjHYzS_TH88Dili94ydti0k11qbLP4nWMOGhhZ3_BBdbH6yqA6L9IK0BnOulO2AAUVfdG1QwuuXlJraFItkQtNu4COFT53V5PkznszsegmciR81kMZpqnqWPDx2PcVn9uF5IndppKWzNitFYf8Z7hdlEJZIFRpiDz83GHeY4S9HGTdLnB_N85Vb-0Lu5nacrvSFyN_J',
      },
      {
        id: 'annihilation',
        title: 'Annihilation',
        year: 2018,
        director: 'Alex Garland',
        runtime: '1h 55m',
        rating: 4.5,
        matchScore: 93,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Horror', 'Mystery'],
        tags: ['Metamorphic Sound', 'Cosmic Horror'],
        overview:
          'A biologist signs up for a dangerous, secret expedition into an environmental disaster zone where the laws of nature do not apply.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCS-zxyG8kWC0hTq_ezUd7_JXg6GWnvGKW0ph4uvq9CQOUsx03gfWh3kHPr_Q7DUnuIS1BXnGDMq2IHuoqlMgSzzh2fP_b-oWJW7Bk3PWCJlNraHljQRxa3DG_U8LNe95552Uue8RWoeeOvZzdGjngQzDLWydldmDmn96g7N6J5H8iwjak0KR8PSxmCj9wt3d-HrbDoEPqmPJ0K1XLixBIKxoRHpkq8ZoaRXBUiD3-e-LJfY7A2tG1y',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCS-zxyG8kWC0hTq_ezUd7_JXg6GWnvGKW0ph4uvq9CQOUsx03gfWh3kHPr_Q7DUnuIS1BXnGDMq2IHuoqlMgSzzh2fP_b-oWJW7Bk3PWCJlNraHljQRxa3DG_U8LNe95552Uue8RWoeeOvZzdGjngQzDLWydldmDmn96g7N6J5H8iwjak0KR8PSxmCj9wt3d-HrbDoEPqmPJ0K1XLixBIKxoRHpkq8ZoaRXBUiD3-e-LJfY7A2tG1y',
      },
      {
        id: 'the-creator',
        title: 'The Creator',
        year: 2023,
        director: 'Gareth Edwards',
        runtime: '2h 13m',
        rating: 4.4,
        matchScore: 91,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Action', 'Adventure'],
        tags: ['FX2 Guerilla', 'Location Scale'],
        overview:
          'Amid a future war between the human race and artificial intelligence, an ex-soldier discovers a weapon disguised as a child.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAKBIhBeszIRPlGrit0Ynhm0GCIQu0m-rzMhCNoLbrQsdEYKJez4HJXAStw2dSOaIIUiCS0YAi-D1mXGhX-4z9U6oJ9UPax5lReRzLYDeOifXWTIAzM3Py7KWA0iDzstw5GjU-tWDbEY61orT6bDUYpTP-UaTyPfsIYXnw0pwuv4RJ3StpzkOXReYhTd0TiGtRE4-l7o7AYwC6R8pzQt2odF94eh8rWEdQwAmbYnllaJMZEYMijC7ka',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAKBIhBeszIRPlGrit0Ynhm0GCIQu0m-rzMhCNoLbrQsdEYKJez4HJXAStw2dSOaIIUiCS0YAi-D1mXGhX-4z9U6oJ9UPax5lReRzLYDeOifXWTIAzM3Py7KWA0iDzstw5GjU-tWDbEY61orT6bDUYpTP-UaTyPfsIYXnw0pwuv4RJ3StpzkOXReYhTd0TiGtRE4-l7o7AYwC6R8pzQt2odF94eh8rWEdQwAmbYnllaJMZEYMijC7ka',
      },
      {
        id: 'everything-everywhere',
        title: 'Everything Everywhere',
        year: 2022,
        director: 'Daniels',
        runtime: '2h 19m',
        rating: 4.8,
        matchScore: 92,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Comedy', 'Adventure'],
        tags: ['Absurdist Heart', 'Kinetic Pacing'],
        overview:
          'A middle-aged Chinese immigrant is swept up into an insane adventure in which she alone can save existence.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCQEKXsA8aeKMo74xmY5s60Rd1tbNpgLKusl0RjrOO-BRTbzi8oG-wwdH_5owiixYKtceqv9A95hDKhNzIIDOHk95mOdGx9N67WcVj59XWKH3TYNuVhayW_6tZuyZze_BfMuD3rV-Dlu4e0trJ8X-RBUl6pcW_royUIi7LJEyzIcTSlbyF093AoW7jPDBV_tXrCaoM2kuRYzhlEK_DBE9vla-Rk9dlvZskiArrTnlI8rTqGNU6c5K1W',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCQEKXsA8aeKMo74xmY5s60Rd1tbNpgLKusl0RjrOO-BRTbzi8oG-wwdH_5owiixYKtceqv9A95hDKhNzIIDOHk95mOdGx9N67WcVj59XWKH3TYNuVhayW_6tZuyZze_BfMuD3rV-Dlu4e0trJ8X-RBUl6pcW_royUIi7LJEyzIcTSlbyF093AoW7jPDBV_tXrCaoM2kuRYzhlEK_DBE9vla-Rk9dlvZskiArrTnlI8rTqGNU6c5K1W',
      },
    ],
  },
  {
    id: 'row-gems',
    title: 'Hidden Gems & Arthouse Discoveries',
    subtitle: 'High critic score • Low mainstream exposure matching your exact curatorial profile.',
    anchorBadge: 'Curatorial Filter',
    iconType: 'diamond',
    movies: [
      {
        id: 'aftersun',
        title: 'Aftersun',
        year: 2022,
        director: 'Charlotte Wells',
        runtime: '1h 42m',
        rating: 4.8,
        matchScore: 94,
        matchBadgeText: 'POPULAR',
        genres: ['Drama'],
        tags: ['Emotional Depth', 'Memory Tape'],
        overview:
          'Sophie reflects on the shared joy and private melancholy of a holiday she took with her father twenty years earlier.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDYPBUrqiH9UW0RG0KjIVQNXJWQ5PKjFkhO-XCPTj8lR-C5rOYeX7kFoU7gKs_fSA9DM1AuLlgzwgPzHMJtF73mjiPs4YUfmzw9RHKheh5h7CRpwTQKl1S2Vt1b5IYRzjr9_k3oeSi5wjfc9HRY4nCqZ6alVkiVHCZaZEQvqTQxxWBLLLA5am0X7aB5aWrfMLPeROUfu200wJcrkt44HPjom5X5BRqD-4xpO9Jy4hnAzGTpxyTogcBI',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDYPBUrqiH9UW0RG0KjIVQNXJWQ5PKjFkhO-XCPTj8lR-C5rOYeX7kFoU7gKs_fSA9DM1AuLlgzwgPzHMJtF73mjiPs4YUfmzw9RHKheh5h7CRpwTQKl1S2Vt1b5IYRzjr9_k3oeSi5wjfc9HRY4nCqZ6alVkiVHCZaZEQvqTQxxWBLLLA5am0X7aB5aWrfMLPeROUfu200wJcrkt44HPjom5X5BRqD-4xpO9Jy4hnAzGTpxyTogcBI',
      },
      {
        id: 'coherence',
        title: 'Coherence',
        year: 2013,
        director: 'James Ward Byrkit',
        runtime: '1h 29m',
        rating: 4.6,
        matchScore: 93,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Mystery', 'Thriller'],
        tags: ['Quantum Puzzle', 'Micro-Budget'],
        overview:
          'Strange things begin to happen when a group of eight friends gather for a dinner party on an evening when an astronomical comet passes overhead.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBQkSmGoUv3OLun0eNxy492cBt0gywyJNzIxXPkl55Wljz4qHnFtHHC8QFVRL6NClPVo-KV0V7jHNQMFYAF3L0Z5Iu1IM5Lrrjd08z9Z6F54lUI_BEumooCmqwpk3kZTfLLWADi3Wn-Letv160YfifJFuhDhEnQknuJBjnn6sO1qYL35WoHguOfFh6YLv_M069NIBhVOw8BLl9CUWDEuk1U66JT9wuVbjcjkGPi4074A8sVDJ3-kLr1',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBQkSmGoUv3OLun0eNxy492cBt0gywyJNzIxXPkl55Wljz4qHnFtHHC8QFVRL6NClPVo-KV0V7jHNQMFYAF3L0Z5Iu1IM5Lrrjd08z9Z6F54lUI_BEumooCmqwpk3kZTfLLWADi3Wn-Letv160YfifJFuhDhEnQknuJBjnn6sO1qYL35WoHguOfFh6YLv_M069NIBhVOw8BLl9CUWDEuk1U66JT9wuVbjcjkGPi4074A8sVDJ3-kLr1',
      },
      {
        id: 'the-vast-of-night',
        title: 'The Vast of Night',
        year: 2019,
        director: 'Andrew Patterson',
        runtime: '1h 31m',
        rating: 4.5,
        matchScore: 90,
        matchBadgeText: 'POPULAR',
        genres: ['Sci-Fi', 'Mystery', 'Drama'],
        tags: ['Steadicam Purity', 'Audio Mystery'],
        overview:
          'In the twilight of the 1950s in New Mexico, a switchboard operator and a radio DJ discover a strange audio frequency.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBFDloT_2axm3SNdeRl0CECMXG2oi8rap43ufZyjIZg9N_VXi_PAa9VUyxCpRSeYxUNtUwg8VmuwR0Ld6n7p92WPGRJuoyCOO7EOFQn6NrLQru2c9DGzWMpggeexd4UGPUSfLClyz5J84c8b1BTYU5PuxyutxVPSwnLNZh1Sj1Vs-64OmfCJO0XxOjOr2aGN-TeAik2qsP480hrcG3Dl6O5xKJIX_78h0DM-68UImqEHFpcBezfvKMw',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBFDloT_2axm3SNdeRl0CECMXG2oi8rap43ufZyjIZg9N_VXi_PAa9VUyxCpRSeYxUNtUwg8VmuwR0Ld6n7p92WPGRJuoyCOO7EOFQn6NrLQru2c9DGzWMpggeexd4UGPUSfLClyz5J84c8b1BTYU5PuxyutxVPSwnLNZh1Sj1Vs-64OmfCJO0XxOjOr2aGN-TeAik2qsP480hrcG3Dl6O5xKJIX_78h0DM-68UImqEHFpcBezfvKMw',
      },
      {
        id: 'portrait-of-a-lady-on-fire',
        title: 'Portrait of a Lady on Fire',
        year: 2019,
        director: 'Céline Sciamma',
        runtime: '2h 2m',
        rating: 4.9,
        matchScore: 91,
        matchBadgeText: 'POPULAR',
        genres: ['Drama', 'Romance'],
        tags: ['Sublime Gaze', 'The Gaze'],
        overview:
          'On an isolated island in Brittany at the end of the eighteenth century, a female painter is obliged to paint a wedding portrait.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDy8Q1ET0clXU5t21UJ97ScDqPX3DwgjRVDz8Dl_IYPkl89-4JAAJn-mxX96hXjgvwrew2J5orIFcB8eIzkQ2vq9WcG6ZfAYLDwAkYiIoD17sdwB_bihXI-Vbm7mYKcYI7tMyu0LTPzalgBY6NoOl6Y0TElKwVcdCSeEM9RSsEVOerxPe5huw-q-X2ukHYkFQ_JYHmw3Eqk8lLZrpYhrxPgEIKQVgxsuA8-sByvypwA10XWRloJwyuH',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuDy8Q1ET0clXU5t21UJ97ScDqPX3DwgjRVDz8Dl_IYPkl89-4JAAJn-mxX96hXjgvwrew2J5orIFcB8eIzkQ2vq9WcG6ZfAYLDwAkYiIoD17sdwB_bihXI-Vbm7mYKcYI7tMyu0LTPzalgBY6NoOl6Y0TElKwVcdCSeEM9RSsEVOerxPe5huw-q-X2ukHYkFQ_JYHmw3Eqk8lLZrpYhrxPgEIKQVgxsuA8-sByvypwA10XWRloJwyuH',
      },
      {
        id: 'burning',
        title: 'Burning',
        year: 2018,
        director: 'Lee Chang-dong',
        runtime: '2h 28m',
        rating: 4.7,
        matchScore: 89,
        matchBadgeText: 'POPULAR',
        genres: ['Drama', 'Mystery', 'Thriller'],
        tags: ['Class Ambiguity', 'Murakami Tone'],
        overview:
          'Jong-su bumps into a girl who once lived in the same neighborhood, who asks him to look after her cat while on a trip to Africa.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAylM1h5SY2Is-Fisx13pIm-Hb2B6YACHDGLV9Pc-016kecjpBCpGOL9yVWlIbo2PWs5aYFJKCcGfhgKzFtKHXzsHTrU6CcNEN7vPgrR-Sq_c61LU37H8RhJ7gIi5RCS0BjYleM6GSqKTgZS5i4692o7inRttqtl_mh9rh5Vi7_Fdv-_W4gzqNn1BqzW36rCOIBY7xFQ79lL2CT1VIGS62g4kZ4YxSCvNOgjl1X3cucvLfFrueThkmf',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAylM1h5SY2Is-Fisx13pIm-Hb2B6YACHDGLV9Pc-016kecjpBCpGOL9yVWlIbo2PWs5aYFJKCcGfhgKzFtKHXzsHTrU6CcNEN7vPgrR-Sq_c61LU37H8RhJ7gIi5RCS0BjYleM6GSqKTgZS5i4692o7inRttqtl_mh9rh5Vi7_Fdv-_W4gzqNn1BqzW36rCOIBY7xFQ79lL2CT1VIGS62g4kZ4YxSCvNOgjl1X3cucvLfFrueThkmf',
      },
      {
        id: 'drive-my-car',
        title: 'Drive My Car',
        year: 2021,
        director: 'Ryusuke Hamaguchi',
        runtime: '2h 59m',
        rating: 4.8,
        matchScore: 92,
        matchBadgeText: 'POPULAR',
        genres: ['Drama'],
        tags: ['Catharsis', 'Dialogue Pace'],
        overview:
          'An aging theater director directs a production of Uncle Vanya while grappling with the sudden death of his wife.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCR4nTWrOXoCIvZnABaAtR9OlJm5ddL1kto01ADLLSCYlJFWNQnQmlt1u4sAUMU70Hoc5DLROXyiCZl7quyMpKf7-zPDV27TRxhn88glrHBsTMmlBYdZgmnle3Db1JcxbHbBcL-3Dl8t8YfPp_8ag6PiMskj3kLR-92_qxHdhbHiVPsIvSgG_mA_Gf_f71NVXJNKzMJhXWVsJKE72m6CChROVRuhur0czHn9XtrukanPmGt2-t0L7zR',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCR4nTWrOXoCIvZnABaAtR9OlJm5ddL1kto01ADLLSCYlJFWNQnQmlt1u4sAUMU70Hoc5DLROXyiCZl7quyMpKf7-zPDV27TRxhn88glrHBsTMmlBYdZgmnle3Db1JcxbHbBcL-3Dl8t8YfPp_8ag6PiMskj3kLR-92_qxHdhbHiVPsIvSgG_mA_Gf_f71NVXJNKzMJhXWVsJKE72m6CChROVRuhur0czHn9XtrukanPmGt2-t0L7zR',
      },
    ],
  },
  {
    id: 'row-trending',
    title: 'Trending in Your Taste Cluster',
    subtitle: 'Disproportionately favored right now by peers with >88% taste affinity overlap.',
    anchorBadge: 'Cluster Convergence',
    iconType: 'trending',
    movies: [
      {
        id: 'challengers',
        title: 'Challengers',
        year: 2024,
        director: 'Luca Guadagnino',
        runtime: '2h 11m',
        rating: 4.6,
        matchScore: 95,
        matchBadgeText: 'POPULAR',
        genres: ['Drama', 'Romance', 'Sport'],
        tags: ['Reznor Score', 'Kinetic Electro'],
        overview:
          'Tashi, a tennis prodigy-turned-coach, takes her champion husband on a redemption tournament against her former lover.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBCrlU9KnKvPtRS5-ag_0vZU0L4Ay1lZypkCp74IK_jSdlZmdzPtnzDNZQwuZVGKwMhJlpO17gNqk7zKohg_6gVdjgbNiXbsIaf0c_8_1rL7gzecj1cHlkgchD5SM4x1IP5VJBNW7uqfVDUPuQ4OYB9aGuKrD9HWz0e7MxHMjbzD-vYbWJUEat-c9Y-03AWCYpFU-ncymykV-4Ixw-2JNRdmQDxJtVswsW5v-nkhVLWQvNHE17yCfX7',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBCrlU9KnKvPtRS5-ag_0vZU0L4Ay1lZypkCp74IK_jSdlZmdzPtnzDNZQwuZVGKwMhJlpO17gNqk7zKohg_6gVdjgbNiXbsIaf0c_8_1rL7gzecj1cHlkgchD5SM4x1IP5VJBNW7uqfVDUPuQ4OYB9aGuKrD9HWz0e7MxHMjbzD-vYbWJUEat-c9Y-03AWCYpFU-ncymykV-4Ixw-2JNRdmQDxJtVswsW5v-nkhVLWQvNHE17yCfX7',
      },
      {
        id: 'poor-things',
        title: 'Poor Things',
        year: 2023,
        director: 'Yorgos Lanthimos',
        runtime: '2h 21m',
        rating: 4.7,
        matchScore: 93,
        matchBadgeText: 'POPULAR',
        genres: ['Comedy', 'Drama', 'Romance', 'Sci-Fi'],
        tags: ['Absurdist Tale', 'Fish-Eye Lenses'],
        overview:
          'The incredible tale about the fantastical evolution of Bella Baxter, a young woman brought back to life by an eccentric scientist.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAJvsRDpjSfswXojfpn6KG5fZOTUr21Q1hFd7_D5T-IeZ1jJqFkhDJJaYrw-N793Akic2MU1EkwMxnpOd2v9xYsmEu29n71QnBv5wyGv5zXL7afJjdV_0_RIowyUPAQo049XgB2I8b3C3cUaNzQPKAQuDYBxwKdbvxp9B-6XcYwkXsodlkWOY29NVJWgb2oGQL8COO_6TnQBzfG3gbKR_KtSVDC4EHt3YGBqkzwxSbsbiBY2uvvDLtI',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAJvsRDpjSfswXojfpn6KG5fZOTUr21Q1hFd7_D5T-IeZ1jJqFkhDJJaYrw-N793Akic2MU1EkwMxnpOd2v9xYsmEu29n71QnBv5wyGv5zXL7afJjdV_0_RIowyUPAQo049XgB2I8b3C3cUaNzQPKAQuDYBxwKdbvxp9B-6XcYwkXsodlkWOY29NVJWgb2oGQL8COO_6TnQBzfG3gbKR_KtSVDC4EHt3YGBqkzwxSbsbiBY2uvvDLtI',
      },
      {
        id: 'civil-war',
        title: 'Civil War',
        year: 2024,
        director: 'Alex Garland',
        runtime: '1h 49m',
        rating: 4.5,
        matchScore: 91,
        matchBadgeText: 'POPULAR',
        genres: ['Action', 'Thriller'],
        tags: ['Photojournalism', 'Visceral Audio'],
        overview:
          'A team of military-embedded journalists embarks on a high-risk journey across a dystopian future America.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCCC6qJB3rCf-mNK0rgsdd4EvZy_6LtCKNjAYBZYDg2KZS7qSIcSFfA3l0u0lxlQgAdvQLR2BHCfyB_i2fAiwgM8AiKTwJQO6UyGfjkKq9L3LmoLFPWBQUIOAXxWV23TQFEOSOXj-Qe50z4U2xbFVE_rKoG9oPb79eE64Zm0wMNQTuALWTjhDE8HcTtA8J5sYnKAtdPwcQmsSjEjE0AOsyyZj6kiBelX11J4AZ9iUDMAPkS3rTfNlrL',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCCC6qJB3rCf-mNK0rgsdd4EvZy_6LtCKNjAYBZYDg2KZS7qSIcSFfA3l0u0lxlQgAdvQLR2BHCfyB_i2fAiwgM8AiKTwJQO6UyGfjkKq9L3LmoLFPWBQUIOAXxWV23TQFEOSOXj-Qe50z4U2xbFVE_rKoG9oPb79eE64Zm0wMNQTuALWTjhDE8HcTtA8J5sYnKAtdPwcQmsSjEjE0AOsyyZj6kiBelX11J4AZ9iUDMAPkS3rTfNlrL',
      },
      {
        id: 'past-lives',
        title: 'Past Lives',
        year: 2023,
        director: 'Celine Song',
        runtime: '1h 45m',
        rating: 4.8,
        matchScore: 94,
        matchBadgeText: 'POPULAR',
        genres: ['Drama', 'Romance'],
        tags: ['Subtle Melancholy', 'In-Yun'],
        overview:
          'Nora and Hae Sung, two deeply connected childhood friends, are reunited in New York for one fateful week.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAkLYb3JRe1Ln3fxCScox2cBJMUAohG3fVzCJAy0VyEwjL1DpTBeLUutSPKgXMgpN4nmh2FwT7efK-anQXhmgfl97W-QE2sDjC-Su2abKublJyKzRR10cHN2DGuPnol0h_v3CRhSHbgzY-LNmIfuHFYbRD98viS3mu0f6GI1tZAUbbEwwMhOvBopwq3k7rGaKb2fplabpTk_QOUR_ABuk-utuUIWUEqWPAX8Ap4EfX-TvRzJ_coH2ng',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuAkLYb3JRe1Ln3fxCScox2cBJMUAohG3fVzCJAy0VyEwjL1DpTBeLUutSPKgXMgpN4nmh2FwT7efK-anQXhmgfl97W-QE2sDjC-Su2abKublJyKzRR10cHN2DGuPnol0h_v3CRhSHbgzY-LNmIfuHFYbRD98viS3mu0f6GI1tZAUbbEwwMhOvBopwq3k7rGaKb2fplabpTk_QOUR_ABuk-utuUIWUEqWPAX8Ap4EfX-TvRzJ_coH2ng',
      },
      {
        id: 'anatomy-of-a-fall',
        title: 'Anatomy of a Fall',
        year: 2023,
        director: 'Justine Triet',
        runtime: '2h 31m',
        rating: 4.8,
        matchScore: 92,
        matchBadgeText: 'POPULAR',
        genres: ['Drama', 'Mystery', 'Crime'],
        tags: ["Palme d'Or", 'Courtroom Dissection'],
        overview:
          'A woman is suspected of murder after her husband\'s death in the snow, and her blind son is the sole witness.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuABBJuJ937BEPyZdBR_u8xufvRZURXvc5ldZLiHPvQ6hsmdTkwVhckU2uXuRSsS_66evtaBjmfP-d3kSFDxFHYqT8s4tLaiCXao4AFt65gjFdxDPsBA-CULLSdgA0UgufCK3o1jrbgcn981nro-v5ZNcbXeqOdyc64U9f2FyW_C99qhZubLonqOdv14Pkjv5oNHZ6qrkfogMTRSFeXCtYcd1LCNvRslesihBG0LlXdF-UGCdn-OPI3p',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuABBJuJ937BEPyZdBR_u8xufvRZURXvc5ldZLiHPvQ6hsmdTkwVhckU2uXuRSsS_66evtaBjmfP-d3kSFDxFHYqT8s4tLaiCXao4AFt65gjFdxDPsBA-CULLSdgA0UgufCK3o1jrbgcn981nro-v5ZNcbXeqOdyc64U9f2FyW_C99qhZubLonqOdv14Pkjv5oNHZ6qrkfogMTRSFeXCtYcd1LCNvRslesihBG0LlXdF-UGCdn-OPI3p',
      },
    ],
  },
  {
    id: 'row-recent',
    title: 'Recently Added to MoieRec',
    subtitle: 'Newly cataloged 4K Criterion transfers, restored film negatives, and remastered soundscapes.',
    anchorBadge: 'Archival Vault Ingest',
    iconType: 'archive',
    movies: [
      {
        id: 'stalker',
        title: 'Stalker',
        year: 1979,
        director: 'Andrei Tarkovsky',
        runtime: '2h 42m',
        rating: 4.9,
        matchScore: 96,
        matchBadgeText: '4K MASTER',
        genres: ['Sci-Fi', 'Drama'],
        tags: ['Existential Lens', 'Mosfilm Scan'],
        overview:
          'A figure known as the Stalker guides two men into a mysterious forbidden area known simply as The Zone.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCskHPA--xfOemtz0-s3AHA_0T76Bg9Ix_6_8k547SA50SmqAT4i_uoZstm_JELyEOppLX5fd-NB5llejRc2f9rGHiM82yVvVgDUTY-ROJjbc082w40QQbwmlPIzM4WcCOUCKSKfD5YE6y8Jp6qrSYv7D7g9yDzkAC3TfPAtB4lyvpVS9pk5WtEugY8llOO1fKYBhvrhelzY6mQVzzBkMr9nWrNb-jHrG2d7LZRxhgrKYHL-7OL_458',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCskHPA--xfOemtz0-s3AHA_0T76Bg9Ix_6_8k547SA50SmqAT4i_uoZstm_JELyEOppLX5fd-NB5llejRc2f9rGHiM82yVvVgDUTY-ROJjbc082w40QQbwmlPIzM4WcCOUCKSKfD5YE6y8Jp6qrSYv7D7g9yDzkAC3TfPAtB4lyvpVS9pk5WtEugY8llOO1fKYBhvrhelzY6mQVzzBkMr9nWrNb-jHrG2d7LZRxhgrKYHL-7OL_458',
      },
      {
        id: 'cure',
        title: 'Cure',
        year: 1997,
        director: 'Kiyoshi Kurosawa',
        runtime: '1h 51m',
        rating: 4.8,
        matchScore: 92,
        matchBadgeText: 'NEW RESTORATION',
        genres: ['Crime', 'Horror', 'Mystery'],
        tags: ['Psychological Dread', 'Hypnosis'],
        overview:
          'A wave of gruesome murders is committed by different people who have no recollection of their crimes.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBhw_LfBInK0SxqvTUeElkoWk9FQGU1RY5OFK38FT-s2FRv5og1ZJ_Pjcv_QffIqfDnWan_B0qKyZNqDFEqUESy9zLlqVt8yxw--4H6x3i2IO1hks_MHkUkqJP98j0GUATHL6o7TkohyJT2OKVEp-ZBZKooVTupa2nLdt2LR9PgaTqPT71g8DTJRkYl_HDgl-uiB9wlVoL9GWTI3asyFtauH_Hfku1hCnJGTZM61sZtYB7QmpouZXJF',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuBhw_LfBInK0SxqvTUeElkoWk9FQGU1RY5OFK38FT-s2FRv5og1ZJ_Pjcv_QffIqfDnWan_B0qKyZNqDFEqUESy9zLlqVt8yxw--4H6x3i2IO1hks_MHkUkqJP98j0GUATHL6o7TkohyJT2OKVEp-ZBZKooVTupa2nLdt2LR9PgaTqPT71g8DTJRkYl_HDgl-uiB9wlVoL9GWTI3asyFtauH_Hfku1hCnJGTZM61sZtYB7QmpouZXJF',
      },
      {
        id: 'persona',
        title: 'Persona',
        year: 1966,
        director: 'Ingmar Bergman',
        runtime: '1h 24m',
        rating: 4.9,
        matchScore: 95,
        matchBadgeText: '4K HDR',
        genres: ['Drama', 'Thriller'],
        tags: ['Duality', 'Sven Nykvist Light'],
        overview:
          'A nurse is put in charge of a mute actress and finds that their personalities begin to merge in disturbing ways.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuB4r4iLrp91sqc8FzW6NpQVVAuJLIc8S9Fn7W5bJkMOE9H9XUO5cXpNIEH42dZG8UHnu92OkpfEPsgj_Xvn14fUracXGw1-KEFEbLoqFGLLkaBB6hhHBn6doC0uDkGfgNEy0gevzq345CvPbtjfBLR6F7a5egZYxdYBHtO1GEkl8anDampFFkXF610BxJmeuDYH1AmYU1N_fsYu44vluH_IC8tDlUyIEQLBv3ldQaeWmpfNpoRCuZI-',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuB4r4iLrp91sqc8FzW6NpQVVAuJLIc8S9Fn7W5bJkMOE9H9XUO5cXpNIEH42dZG8UHnu92OkpfEPsgj_Xvn14fUracXGw1-KEFEbLoqFGLLkaBB6hhHBn6doC0uDkGfgNEy0gevzq345CvPbtjfBLR6F7a5egZYxdYBHtO1GEkl8anDampFFkXF610BxJmeuDYH1AmYU1N_fsYu44vluH_IC8tDlUyIEQLBv3ldQaeWmpfNpoRCuZI-',
      },
      {
        id: 'ran',
        title: 'Ran',
        year: 1985,
        director: 'Akira Kurosawa',
        runtime: '2h 40m',
        rating: 4.9,
        matchScore: 94,
        matchBadgeText: '4K MASTER',
        genres: ['Action', 'Drama', 'War'],
        tags: ['Tragic Scale', 'King Lear Allegory'],
        overview:
          'In medieval Japan, an elderly warlord retires and hands over power to his three sons, triggering catastrophic war.',
        poster:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCpbzNnUZXYoSfSQOqO3wroLzQKGICMOs7Iqt1dUNnkSES5wkzUiwHtWoBm3n2QjC-3QZggWfOmEH42LjkGlZ9Y3eO1vREFCOz7d84fXdVZt5ZsxZkk_RcjFOAWNwyhNZOEYZqLI_fgdl-qh05iXK-LbbAf6I6WEOIGyN2k5hgap-XnrXxW7zyf4IEYA2B3siLlnFGoU2thgytq_Y69x2SwALhDuKQQLcpXOPyLx3FAH0FgJ90wvhXE',
        backdrop:
          'https://lh3.googleusercontent.com/aida-public/AB6AXuCpbzNnUZXYoSfSQOqO3wroLzQKGICMOs7Iqt1dUNnkSES5wkzUiwHtWoBm3n2QjC-3QZggWfOmEH42LjkGlZ9Y3eO1vREFCOz7d84fXdVZt5ZsxZkk_RcjFOAWNwyhNZOEYZqLI_fgdl-qh05iXK-LbbAf6I6WEOIGyN2k5hgap-XnrXxW7zyf4IEYA2B3siLlnFGoU2thgytq_Y69x2SwALhDuKQQLcpXOPyLx3FAH0FgJ90wvhXE',
      },
    ],
  },
];

export const ALL_MOCK_MOVIES: Movie[] = [
  HERO_MOVIE,
  ...MOCK_RECOMMENDATION_ROWS.flatMap((row) => row.movies),
];
