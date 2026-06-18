
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_validation():
    driver = webdriver.Chrome()
    try:
        driver.get("http://localhost:8000/planning")
        
        # Click "New" (Wait for load)
        time.sleep(2)
        
        # Try to save without entering product
        save_btn = driver.find_element(By.ID, "btnConfirm")
        # Ensure it's visible/clickable (it might be hidden if status is confined)
        # Actually in 'new' state btnConfirm should say "Confirmar Planificación"
        
        if save_btn.is_displayed():
            save_btn.click()
            
            # Check for alert
            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print(f"Alert Text: {alert.text}")
                if "seleccione un producto" in alert.text:
                    print("SUCCESS: Validation Alert appeared.")
                    alert.accept()
                else:
                    print(f"FAILURE: Unexpected alert text: {alert.text}")
            except:
                print("FAILURE: No alert appeared.")
        else:
            print("Save button not visible.")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_validation()
