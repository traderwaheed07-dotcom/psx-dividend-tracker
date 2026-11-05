set -e
P=apk/app/src/main
mkdir -p $P/java/com/waheedali/psxdividends $P/res/values $P/res/mipmap-xxxhdpi

if [ -f icon-192.png ]; then
  cp icon-192.png $P/res/mipmap-xxxhdpi/ic_launcher.png
else
  convert -size 192x192 xc:'#0d5c4a' -fill '#f5c451' -gravity center -pointsize 64 -annotate 0 'PSX' $P/res/mipmap-xxxhdpi/ic_launcher.png
fi

cat > apk/settings.gradle <<'EOF'
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = 'PSXDividends'
include ':app'
EOF

cat > apk/build.gradle <<'EOF'
plugins {
    id 'com.android.application' version '8.5.2' apply false
}
EOF

cat > apk/gradle.properties <<'EOF'
org.gradle.jvmargs=-Xmx2g
android.useAndroidX=false
android.nonTransitiveRClass=true
EOF

cat > apk/app/build.gradle <<'EOF'
plugins {
    id 'com.android.application'
}
android {
    namespace 'com.waheedali.psxdividends'
    compileSdk 34
    defaultConfig {
        applicationId 'com.waheedali.psxdividends'
        minSdk 24
        targetSdk 34
        versionCode 1
        versionName '1.0'
    }
    compileOptions {
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }
}
EOF

cat > $P/AndroidManifest.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <application
        android:label="PSX Dividends"
        android:icon="@mipmap/ic_launcher"
        android:theme="@style/AppTheme"
        android:allowBackup="true"
        android:usesCleartextTraffic="false">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

cat > $P/res/values/styles.xml <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="android:Theme.Material.Light.NoActionBar">
        <item name="android:statusBarColor">#0D5C4A</item>
        <item name="android:navigationBarColor">#0F1715</item>
        <item name="android:windowBackground">@android:color/black</item>
    </style>
</resources>
EOF

cat > $P/java/com/waheedali/psxdividends/MainActivity.java <<'EOF'
package com.waheedali.psxdividends;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    static final String HOME = "https://traderwaheed07-dotcom.github.io/psx-dividend-tracker/";
    static final String HOST = "traderwaheed07-dotcom.github.io";
    WebView web;

    boolean online() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo ni = cm == null ? null : cm.getActiveNetworkInfo();
        return ni != null && ni.isConnected();
    }

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        web = new WebView(this);
        web.setBackgroundColor(0xFF0F1715);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setCacheMode(online() ? WebSettings.LOAD_DEFAULT : WebSettings.LOAD_CACHE_ELSE_NETWORK);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                Uri u = r.getUrl();
                String sch = u.getScheme();
                if (("https".equals(sch) || "http".equals(sch)) && HOST.equals(u.getHost())) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, u));
                } catch (Exception e) {
                    // no app can open this link
                }
                return true;
            }
        });
        if (saved == null) {
            web.loadUrl(HOME);
        } else {
            web.restoreState(saved);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }
}
EOF

find apk -type f | sort
