"""
Cookie management utilities for web scraping and data downloads.

This module provides functionality to classify, filter, and manage HTTP cookies
with a focus on privacy and only keeping necessary cookies.
"""

from requests.cookies import RequestsCookieJar


def print_cookie_details(cookies, title="Cookies"):
    """
    Print detailed information about cookies.
    
    Args:
        cookies: Collection of cookie objects
        title (str): Title for the output section
    """
    print(f"\n=== {title} ===")
    print(f"Total cookies: {len(cookies)}")
    
    for cookie in cookies:
        print(f"\nCookie: {cookie.name}")
        print(f"  Value: {cookie.value[:50]}{'...' if len(cookie.value) > 50 else ''}")
        print(f"  Domain: {cookie.domain}")
        print(f"  Path: {cookie.path}")
        print(f"  Secure: {cookie.secure}")
        print(f"  HttpOnly: {hasattr(cookie, 'has_nonstandard_attr') and cookie.has_nonstandard_attr('HttpOnly')}")
        print(f"  Expires: {cookie.expires}")
        print(f"  SameSite: {getattr(cookie, 'same_site', 'Not set')}")
        
        # Try to determine if cookie is necessary or optional
        cookie_type = classify_cookie(cookie.name, cookie.value)
        print(f"  Classification: {cookie_type}")


def classify_cookie(name, value):
    """
    Classify cookies as necessary, functional, analytics, or marketing.
    
    Args:
        name (str): Cookie name
        value (str): Cookie value
        
    Returns:
        str: Classification of the cookie
    """
    name_lower = name.lower()
    
    # Necessary cookies (required for basic functionality)
    necessary_patterns = [
        'session', 'csrf', 'xsrf', 'auth', 'login', 'security',
        'audience', 'jsessionid', 'phpsessid', 'asp.net_sessionid',
        'cookieconsent', 'gdpr', 'ccpa', 'necessary'
    ]
    
    # Analytics/tracking cookies (optional)
    analytics_patterns = [
        'ga', 'gtm', 'gtag', '_gid', '_gat', 'analytics', 'tracking',
        'omniture', 'adobe', 'mixpanel', 'hotjar', 'mouseflow'
    ]
    
    # Marketing/advertising cookies (optional)
    marketing_patterns = [
        'doubleclick', 'facebook', 'twitter', 'linkedin', 'youtube',
        'advertising', 'ads', 'marketing', 'retargeting', 'conversion'
    ]
    
    for pattern in necessary_patterns:
        if pattern in name_lower:
            return "NECESSARY"
    
    for pattern in analytics_patterns:
        if pattern in name_lower:
            return "ANALYTICS (Optional)"
    
    for pattern in marketing_patterns:
        if pattern in name_lower:
            return "MARKETING (Optional)"
    
    # Default classification based on common patterns
    if len(value) > 100 or 'tracking' in value.lower():
        return "LIKELY TRACKING (Optional)"
    
    return "UNKNOWN (Treating as Optional)"


def filter_necessary_cookies(session, verbose=True):
    """
    Filter cookies to keep only necessary ones.
    
    Args:
        session: Requests session object
        verbose (bool): Whether to print detailed filtering information
        
    Returns:
        session: Modified session with filtered cookies
    """
    if verbose:
        print("\n=== Filtering Cookies ===")
    
    original_cookies = list(session.cookies)
    
    if verbose:
        print_cookie_details(original_cookies, "All Received Cookies")
    
    # Create new cookie jar with only necessary cookies
    necessary_jar = RequestsCookieJar()
    
    for cookie in original_cookies:
        classification = classify_cookie(cookie.name, cookie.value)
        if "NECESSARY" in classification:
            necessary_jar.set_cookie(cookie)
            if verbose:
                print(f"\n✓ KEEPING: {cookie.name} - {classification}")
        else:
            if verbose:
                print(f"\n✗ REJECTING: {cookie.name} - {classification}")
    
    # Replace session cookies with filtered ones
    session.cookies = necessary_jar
    
    if verbose:
        print(f"\nCookie filtering complete:")
        print(f"  Original: {len(original_cookies)} cookies")
        print(f"  Kept: {len(session.cookies)} necessary cookies")
        print(f"  Rejected: {len(original_cookies) - len(session.cookies)} optional cookies")
        
        print_cookie_details(session.cookies, "Final Necessary Cookies")
    
    return session


class CookieManager:
    """
    A class to manage cookies for web requests with privacy-focused filtering.
    """
    
    def __init__(self, verbose=True):
        """
        Initialize the CookieManager.
        
        Args:
            verbose (bool): Whether to print detailed information
        """
        self.verbose = verbose
    
    def setup_session_cookies(self, session, initial_url, headers=None):
        """
        Set up session with initial cookies from a URL, then filter them.
        
        Args:
            session: Requests session object
            initial_url (str): URL to visit to collect initial cookies
            headers (dict): Optional headers to use for the request
            
        Returns:
            session: Session with filtered cookies
        """
        if self.verbose:
            print(f"Getting initial cookies from: {initial_url}")
        
        try:
            response = session.get(initial_url, headers=headers or {})
            if self.verbose:
                print(f"Initial page status: {response.status_code}")
                print(f"Initial cookies received: {len(session.cookies)} cookies")
            
            # Filter cookies to keep only necessary ones
            session = filter_necessary_cookies(session, verbose=self.verbose)
            
            return session
            
        except Exception as e:
            if self.verbose:
                print(f"Error getting initial cookies: {e}")
            return session
    
    def get_cookie_summary(self, session):
        """
        Get a summary of cookies in the session.
        
        Args:
            session: Requests session object
            
        Returns:
            dict: Summary of cookie information
        """
        cookies = list(session.cookies)
        summary = {
            'total_cookies': len(cookies),
            'necessary': 0,
            'analytics': 0,
            'marketing': 0,
            'unknown': 0,
            'cookies': []
        }
        
        for cookie in cookies:
            classification = classify_cookie(cookie.name, cookie.value)
            cookie_info = {
                'name': cookie.name,
                'domain': cookie.domain,
                'path': cookie.path,
                'secure': cookie.secure,
                'classification': classification
            }
            summary['cookies'].append(cookie_info)
            
            if 'NECESSARY' in classification:
                summary['necessary'] += 1
            elif 'ANALYTICS' in classification:
                summary['analytics'] += 1
            elif 'MARKETING' in classification:
                summary['marketing'] += 1
            else:
                summary['unknown'] += 1
        
        return summary
