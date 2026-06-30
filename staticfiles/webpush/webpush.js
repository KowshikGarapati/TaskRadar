async function webPushSubscribe() {
    try {
        const reg = await navigator.serviceWorker.ready;

        // Check for existing subscription
        const existing = await reg.pushManager.getSubscription();
        if (existing) {
            console.log("Found existing subscription. Unsubscribing...");
            await existing.unsubscribe();
            console.log("Unsubscribed successfully.");
        }

        // Ask permission
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
            console.log("Notification permission denied");
            return;
        }

        // Subscribe again with the right VAPID key
        const sub = await reg.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array("BMov4lzyLO5ZFKs5uuCXHtmE0yo6Z7-cTpth3oQVrgWroh07h0lQM6neggYlc8AGd5vj0cunf_QwmB0Gqhgb44Q")
        });

        console.log("New subscription:", sub);

        // Send to backend
        await fetch("/save_subscription/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(sub)
        });

        console.log("Subscription saved!");
    } catch (err) {
        console.error("Push subscription failed:", err);
    }
}
// webpush.js

// Utility: convert base64 public key to Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// 👇 paste your NEW public VAPID key here (from settings.py)
const vapidPublicKey = "BMov4lzyLO5ZFKs5uuCXHtmE0yo6Z7-cTpth3oQVrgWroh07h0lQM6neggYlc8AGd5vj0cunf_QwmB0Gqhgb44Q";

async function initPush() {
    if (!("serviceWorker" in navigator)) {
        console.error("Service workers are not supported in this browser");
        return;
    }

    try {
        // Register service worker
        const registration = await navigator.serviceWorker.register("/service_worker.js");
        console.log("✅ Service Worker registered");

        // Check for old subscription
        let oldSub = await registration.pushManager.getSubscription();
        if (!(oldSub)) {
            console.log("⚠️ No existing subscription... subscribing fresh");
            //await oldSub.unsubscribe();


            // Subscribe with new VAPID key
            const newSub = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
            });

            console.log("✅ New subscription created:", newSub);

            // Send to backend
            fetch("/save_subscription/", {
        method: "POST",
        body: JSON.stringify(newSub),
        headers: { "Content-Type": "application/json" }
        })
        .then(res => res.json())
        .then(data => console.log("Subscription saved:", data))
        .catch(err => console.error("Error saving subscription:", err));


                console.log("✅ Subscription sent to backend");
        }else{
            console.log("Already subscribtion exists:", oldSub );
        }
    } catch (err) {
        console.error("❌ Push subscription error:", err);
    }
    
}

// Run as soon as page loads
initPush();
