// @ts-nocheck
import { apiUrl } from '../config/api';
import { useGoogleLogin } from '@react-oauth/google';
import AppleSignin from 'react-apple-signin-auth';
import { useState } from 'react';
import styles from './LoginPage.module.css';

interface Props {
  onLoginSuccess: (token: string) => void;
}

export default function LoginPage({ onLoginSuccess }: Props) {
  const [errorMsg, setErrorMsg] = useState('');

  // ---------------- Google Login ---------------- //
  const loginWithGoogle = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      try {
        const res = await fetch(apiUrl('/auth/google/'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: tokenResponse.access_token }),
        });
        const data = await res.json();
        if (data.key) onLoginSuccess(data.key);
        else setErrorMsg('Authentication failed on the server.');
      } catch (err) {
        setErrorMsg('Network error connecting to backend.');
      }
    },
    onError: () => setErrorMsg('Google Login Failed.'),
  });

  // ---------------- Apple Login ---------------- //
  const handleAppleResponse = async (response: any) => {
    if (!response.authorization) {
      setErrorMsg('Apple Login Failed or Cancelled.');
      return;
    }
    try {
      const res = await fetch(apiUrl('/auth/apple/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: response.authorization.id_token }),
      });
      const data = await res.json();
      if (data.key) onLoginSuccess(data.key);
      else setErrorMsg('Apple Authentication failed on the server. Do you have valid Developer Keys?');
    } catch (err) {
      setErrorMsg('Network error connecting to backend.');
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h2>UPSC Aspire</h2>
          <p>Sign in to access premium mock exams and track your progress.</p>
        </div>
        
        {errorMsg && (
          <div className={styles.errorBanner}>
            {errorMsg}
          </div>
        )}

        <div className={styles.buttons}>
          <button className={`${styles.authBtn} ${styles.googleBtn}`} onClick={() => loginWithGoogle()}>
            <svg viewBox="0 0 24 24" className={styles.icon} xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
          
          <AppleSignin
            authOptions={{
              clientId: 'paste_your_apple_service_id_here',
              scope: 'email name',
              redirectURI: 'https://your-live-domain.com/auth/apple/callback',
              state: 'state',
              nonce: 'nonce',
              usePopup: true
            }}
            uiType="dark"
            className={`${styles.authBtn} ${styles.appleBtn}`}
            noDefaultStyle={false}
            buttonExtraChildren="Continue with Apple"
            onSuccess={handleAppleResponse}
            onError={(error: any) => setErrorMsg('Apple Login Error: ' + (error.error || 'Unknown'))}
            skipScript={false}
            iconProp={{ style: { marginTop: '10px' } }}
            render={(props: any) => (
              <button {...props} className={`${styles.authBtn} ${styles.appleBtn}`}>
                <svg viewBox="0 0 384 512" className={styles.icon} fill="currentColor">
                  <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 24 184.5 15.6 235.9c-8.1 48.8 3.8 97.6 17.5 127.3 14.3 30.9 44.5 86.8 75.3 86.2 30.5-.5 44.4-18.8 81.3-18.8 36.6 0 49.3 18.3 81.3 18.3 32.5-.5 59.8-51 73.8-82.5 14.3-32.3-25.7-49.6-26.1-97.7zM258.3 101.4c17.5-21.2 31.7-49.5 28.5-77.8-25.5 1.1-55.8 17.1-73.8 38.3-16.1 18.8-31 47.7-27.1 75.3 28.3 2.2 55.4-14.6 72.4-35.8z" />
                </svg>
                Continue with Apple
              </button>
            )}
          />
        </div>
      </div>
    </div>
  );
}
