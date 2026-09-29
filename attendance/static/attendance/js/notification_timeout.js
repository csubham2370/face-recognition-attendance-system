(function () {
    "use strict";

    const notificationDuration = 6000;
    const timers = new WeakMap();

    function scheduleDismissal(notification) {
        const currentTimer = timers.get(notification);
        if (currentTimer) {
            window.clearTimeout(currentTimer);
        }

        if (notification.classList.contains("d-none") || !notification.textContent.trim()) {
            return;
        }

        timers.set(
            notification,
            window.setTimeout(function () {
                notification.classList.add("d-none");
                timers.delete(notification);
            }, notificationDuration)
        );
    }

    function findNotifications(node) {
        if (!(node instanceof Element)) {
            return;
        }

        if (node.matches(".alert")) {
            scheduleDismissal(node);
        }

        node.querySelectorAll(".alert").forEach(scheduleDismissal);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".alert").forEach(scheduleDismissal);

        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === "childList") {
                    mutation.addedNodes.forEach(findNotifications);
                    if (mutation.target.closest) {
                        const parentNotification = mutation.target.closest(".alert");
                        if (parentNotification) {
                            scheduleDismissal(parentNotification);
                        }
                    }
                } else if (
                    mutation.type === "attributes" &&
                    mutation.target.matches(".alert")
                ) {
                    scheduleDismissal(mutation.target);
                }
            });
        });

        observer.observe(document.body, {
            attributes: true,
            attributeFilter: ["class"],
            childList: true,
            subtree: true,
        });
    });
})();
