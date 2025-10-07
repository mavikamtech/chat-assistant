import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
} from 'amazon-cognito-identity-js';
import Cookies from 'js-cookie';

const userPoolId = process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || '';
const clientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '';

const userPool = new CognitoUserPool({
  UserPoolId: userPoolId,
  ClientId: clientId,
});

export interface AuthUser {
  email: string;
  name: string;
  idToken: string;
  accessToken: string;
  refreshToken: string;
}

export const signIn = (email: string, password: string): Promise<AuthUser> => {
  return new Promise((resolve, reject) => {
    const authenticationDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    const cognitoUser = new CognitoUser({
      Username: email,
      Pool: userPool,
    });

    cognitoUser.authenticateUser(authenticationDetails, {
      onSuccess: (session: CognitoUserSession) => {
        const idToken = session.getIdToken().getJwtToken();
        const accessToken = session.getAccessToken().getJwtToken();
        const refreshToken = session.getRefreshToken().getToken();

        // Get user attributes
        cognitoUser.getUserAttributes((err, attributes) => {
          if (err) {
            reject(err);
            return;
          }

          const name = attributes?.find(attr => attr.Name === 'name')?.Value || email;

          const user: AuthUser = {
            email,
            name,
            idToken,
            accessToken,
            refreshToken,
          };

          // Store tokens in cookies
          Cookies.set('idToken', idToken, { expires: 1, secure: true, sameSite: 'strict' });
          Cookies.set('accessToken', accessToken, { expires: 1, secure: true, sameSite: 'strict' });
          Cookies.set('refreshToken', refreshToken, { expires: 7, secure: true, sameSite: 'strict' });
          Cookies.set('userEmail', email, { expires: 7, secure: true, sameSite: 'strict' });
          Cookies.set('userName', name, { expires: 7, secure: true, sameSite: 'strict' });

          resolve(user);
        });
      },
      onFailure: (err) => {
        reject(err);
      },
    });
  });
};

export const signOut = () => {
  const cognitoUser = userPool.getCurrentUser();
  if (cognitoUser) {
    cognitoUser.signOut();
  }

  // Clear cookies
  Cookies.remove('idToken');
  Cookies.remove('accessToken');
  Cookies.remove('refreshToken');
  Cookies.remove('userEmail');
  Cookies.remove('userName');
};

export const getCurrentUser = (): { email: string; name: string } | null => {
  const email = Cookies.get('userEmail');
  const name = Cookies.get('userName');
  const idToken = Cookies.get('idToken');

  if (email && name && idToken) {
    return { email, name };
  }

  return null;
};

export const getIdToken = (): string | undefined => {
  return Cookies.get('idToken');
};

export const isAuthenticated = (): boolean => {
  return !!Cookies.get('idToken');
};
