/*!
* Start Bootstrap - Resume v7.0.6 (https://startbootstrap.com/theme/resume)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-resume/blob/master/LICENSE)
*/
//
// Scripts
// 

window.addEventListener('DOMContentLoaded', event => {

    // Activate Bootstrap scrollspy on the main nav element
    const sideNav = document.body.querySelector('#sideNav');
    if (sideNav) {
        new bootstrap.ScrollSpy(document.body, {
            target: '#sideNav',
            rootMargin: '0px 0px -40%',
        });

        const toggleScrolled = () => {
            if (window.scrollY > 30) {
                sideNav.classList.add('scrolled');
            } else {
                sideNav.classList.remove('scrolled');
            }
        };
        toggleScrolled();
        window.addEventListener('scroll', toggleScrolled);
    };

    // Collapse responsive navbar when toggler is visible
    const navbarToggler = document.body.querySelector('.navbar-toggler');
    const responsiveNavItems = [].slice.call(
        document.querySelectorAll('#navbarResponsive .nav-link')
    );
    responsiveNavItems.map(function (responsiveNavItem) {
        responsiveNavItem.addEventListener('click', () => {
            if (window.getComputedStyle(navbarToggler).display !== 'none') {
                navbarToggler.click();
            }
        });
    });

    // Reorder upcoming events by nearest date and show next date/time (requires jQuery)
    if (window.jQuery) {
        const $ = window.jQuery;
        const $list = $('#upcoming-list');
        if ($list.length) {
            const now = new Date();
            const parseTime = (timeStr) => {
                const [h, m] = timeStr.split(':').map(Number);
                return { h: h ?? 0, m: m ?? 0 };
            };

            const nextOccurrence = (day, timeStr) => {
                const { h, m } = parseTime(timeStr);
                const candidate = new Date(now);
                candidate.setHours(h, m, 0, 0);
                const dayDiff = (day - now.getDay() + 7) % 7;
                const needsNextWeek = dayDiff === 0 && candidate <= now;
                candidate.setDate(now.getDate() + (needsNextWeek ? 7 : dayDiff));
                return candidate;
            };

            const items = $list.children('li').map(function () {
                const $li = $(this);
                const day = Number($li.data('day'));
                const time = String($li.data('start') || '00:00');
                const nextDate = nextOccurrence(day, time);
                const dateLabel = nextDate.toLocaleString('id-ID', {
                    weekday: 'long',
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                $li.find('.next-date').text(`Jadwal terdekat: ${dateLabel}`);
                return { el: $li, when: nextDate };
            }).get();

            items.sort((a, b) => a.when - b.when);
            items.forEach(item => $list.append(item.el));
        }
    }

});
