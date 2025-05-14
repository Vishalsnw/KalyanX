import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
from datetime import datetime


def evaluate_model(model_path, test_data, target_column, feature_columns=None):
    """
    Evaluate ML model performance on test data
    
    Args:
        model_path: Path to the saved model file
        test_data: DataFrame containing test data
        target_column: Name of the target column
        feature_columns: List of feature column names (if None, uses model's stored feature list)
    
    Returns:
        Dictionary containing evaluation metrics
    """
    # Load model
    model_data = joblib.load(model_path)
    
    # Use model's stored features if not specified
    if feature_columns is None:
        if 'features' in model_data:
            feature_columns = model_data['features']
        else:
            raise ValueError("Feature columns not specified and not stored in model")
    
    # Extract features and target
    X_test = test_data[feature_columns].copy()
    y_test = test_data[target_column].values
    
    # Apply scaling if available
    if 'scaler' in model_data:
        scaler = model_data['scaler']
        X_test_scaled = scaler.transform(X_test)
    else:
        X_test_scaled = X_test
    
    # Get model and make predictions
    if 'model' in model_data:
        model = model_data['model']
    elif 'first_digit' in model_data and 'last_digit' in model_data:
        # Special case for open/close digit models
        return evaluate_digit_model(model_data, X_test_scaled, test_data, target_column)
    else:
        raise ValueError("Model structure not recognized")
    
    # Make predictions
    y_pred = model.predict(X_test_scaled)
    
    # Calculate metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, average='macro', zero_division=0),
        'recall': recall_score(y_test, y_pred, average='macro', zero_division=0),
        'f1': f1_score(y_test, y_pred, average='macro', zero_division=0),
        'confusion_matrix': confusion_matrix(y_test, y_pred)
    }
    
    return metrics


def evaluate_digit_model(model_data, X_test_scaled, test_data, target_prefix):
    """
    Evaluate digit model performance (special case for open/close digit models)
    
    Args:
        model_data: Loaded model data containing first_digit and last_digit models
        X_test_scaled: Scaled test features
        test_data: Original test data DataFrame
        target_prefix: Prefix for target columns (e.g., 'open' or 'close')
    
    Returns:
        Dictionary containing evaluation metrics
    """
    # Get models
    model_first = model_data['first_digit']
    model_last = model_data['last_digit']
    
    # Make predictions
    y_first_pred = model_first.predict(X_test_scaled)
    y_last_pred = model_last.predict(X_test_scaled)
    
    # Get true values
    y_first_true = test_data[f'{target_prefix}_first'].values
    y_last_true = test_data[f'{target_prefix}_last'].values
    
    # Calculate metrics for first digit
    metrics_first = {
        'accuracy': accuracy_score(y_first_true, y_first_pred),
        'precision': precision_score(y_first_true, y_first_pred, average='macro', zero_division=0),
        'recall': recall_score(y_first_true, y_first_pred, average='macro', zero_division=0),
        'f1': f1_score(y_first_true, y_first_pred, average='macro', zero_division=0),
        'confusion_matrix': confusion_matrix(y_first_true, y_first_pred)
    }
    
    # Calculate metrics for last digit
    metrics_last = {
        'accuracy': accuracy_score(y_last_true, y_last_pred),
        'precision': precision_score(y_last_true, y_last_pred, average='macro', zero_division=0),
        'recall': recall_score(y_last_true, y_last_pred, average='macro', zero_division=0),
        'f1': f1_score(y_last_true, y_last_pred, average='macro', zero_division=0),
        'confusion_matrix': confusion_matrix(y_last_true, y_last_pred)
    }
    
    # Calculate combined accuracy (both digits correct)
    combined_correct = (y_first_pred == y_first_true) & (y_last_pred == y_last_true)
    combined_accuracy = np.mean(combined_correct)
    
    # Combine metrics
    metrics = {
        'first_digit': metrics_first,
        'last_digit': metrics_last,
        'combined_accuracy': combined_accuracy
    }
    
    return metrics


def generate_evaluation_report(model_path, test_data, target_column, feature_columns=None, output_dir='model_reports'):
    """
    Generate comprehensive evaluation report for a model
    
    Args:
        model_path: Path to the saved model file
        test_data: DataFrame containing test data
        target_column: Name of the target column
        feature_columns: List of feature column names
        output_dir: Directory to save the report
    
    Returns:
        Path to the generated report
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get model name from path
    model_name = os.path.basename(model_path).replace('.joblib', '')
    
    # Evaluate model
    metrics = evaluate_model(model_path, test_data, target_column, feature_columns)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create report filename
    report_path = os.path.join(output_dir, f"{model_name}_report_{timestamp}.txt")
    
    # Write report
    with open(report_path, 'w') as f:
        f.write(f"Evaluation Report for {model_name}\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if 'first_digit' in metrics and 'last_digit' in metrics:
            # Handle digit model
            f.write("First Digit Metrics:\n")
            f.write(f"  Accuracy: {metrics['first_digit']['accuracy']:.4f}\n")
            f.write(f"  Precision: {metrics['first_digit']['precision']:.4f}\n")
            f.write(f"  Recall: {metrics['first_digit']['recall']:.4f}\n")
            f.write(f"  F1 Score: {metrics['first_digit']['f1']:.4f}\n\n")
            
            f.write("Last Digit Metrics:\n")
            f.write(f"  Accuracy: {metrics['last_digit']['accuracy']:.4f}\n")
            f.write(f"  Precision: {metrics['last_digit']['precision']:.4f}\n")
            f.write(f"  Recall: {metrics['last_digit']['recall']:.4f}\n")
            f.write(f"  F1 Score: {metrics['last_digit']['f1']:.4f}\n\n")
            
            f.write(f"Combined Accuracy (both digits correct): {metrics['combined_accuracy']:.4f}\n\n")
        else:
            # Handle standard model
            f.write("Model Metrics:\n")
            f.write(f"  Accuracy: {metrics['accuracy']:.4f}\n")
            f.write(f"  Precision: {metrics['precision']:.4f}\n")
            f.write(f"  Recall: {metrics['recall']:.4f}\n")
            f.write(f"  F1 Score: {metrics['f1']:.4f}\n\n")
        
        f.write("Test Dataset Info:\n")
        f.write(f"  Number of samples: {len(test_data)}\n")
        f.write(f"  Target column: {target_column}\n")
        f.write(f"  Features used: {feature_columns}\n\n")
    
    # Generate confusion matrix plot for non-digit models
    if 'first_digit' not in metrics:
        plt.figure(figsize=(10, 8))
        cm = metrics['confusion_matrix']
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.xlabel('Predicted')
        plt.ylabel('True')
        plt.title(f'Confusion Matrix - {model_name}')
        plt.tight_layout()
        
        # Save plot
        plt.savefig(os.path.join(output_dir, f"{model_name}_confusion_matrix_{timestamp}.png"))
        plt.close()
    
    return report_path


def compare_models(model_paths, test_data, target_column, feature_columns=None):
    """
    Compare multiple models on the same test data
    
    Args:
        model_paths: List of paths to saved model files
        test_data: DataFrame containing test data
        target_column: Name of the target column
        feature_columns: List of feature column names
    
    Returns:
        DataFrame with comparison metrics
    """
    results = []
    
    for model_path in model_paths:
        model_name = os.path.basename(model_path).replace('.joblib', '')
        metrics = evaluate_model(model_path, test_data, target_column, feature_columns)
        
        if 'first_digit' in metrics and 'last_digit' in metrics:
            # Handle digit model
            result = {
                'model_name': model_name,
                'first_digit_accuracy': metrics['first_digit']['accuracy'],
                'last_digit_accuracy': metrics['last_digit']['accuracy'],
                'combined_accuracy': metrics['combined_accuracy'],
                'first_digit_f1': metrics['first_digit']['f1'],
                'last_digit_f1': metrics['last_digit']['f1']
            }
        else:
            # Handle standard model
            result = {
                'model_name': model_name,
                'accuracy': metrics['accuracy'],
                'precision': metrics['precision'],
                'recall': metrics['recall'],
                'f1': metrics['f1']
            }
        
        results.append(result)
    
    return pd.DataFrame(results)


def analyze_feature_importance(model_path, feature_names=None):
    """
    Analyze feature importance for a trained model
    
    Args:
        model_path: Path to the saved model file
        feature_names: List of feature names (if None, uses model's stored feature list)
    
    Returns:
        DataFrame with feature importance scores
    """
    # Load model
    model_data = joblib.load(model_path)
    
    # Get model
    if 'model' in model_data:
        model = model_data['model']
    elif 'first_digit' in model_data and 'last_digit' in model_data:
        # Special case for digit models
        return {
            'first_digit': analyze_digit_model_importance(model_data['first_digit'], feature_names),
            'last_digit': analyze_digit_model_importance(model_data['last_digit'], feature_names)
        }
    else:
        raise ValueError("Model structure not recognized")
    
    # Get feature names
    if feature_names is None:
        if 'features' in model_data:
            feature_names = model_data['features']
        else:
            feature_names = [f"feature_{i}" for i in range(model.n_features_in_)]
    
    # Extract feature importance
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
    elif hasattr(model, 'coef_'):
        importances = np.abs(model.coef_).mean(axis=0) if model.coef_.ndim > 1 else np.abs(model.coef_)
    else:
        raise ValueError("Model doesn't provide feature importance information")
    
    # Create DataFrame
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    })
    
    # Sort by importance
    importance_df = importance_df.sort_values('importance', ascending=False).reset_index(drop=True)
    
    return importance_df


def analyze_digit_model_importance(model, feature_names=None):
    """
    Analyze feature importance for a digit model
    
    Args:
        model: The trained model
        feature_names: List of feature names
    
    Returns:
        DataFrame with feature importance scores
    """
    if not hasattr(model, 'feature_importances_'):
        raise ValueError("Model doesn't provide feature importance information")
    
    importances = model.feature_importances_
    
    if feature_names is None:
        feature_names = [f"feature_{i}" for i in range(len(importances))]
    
    # Create DataFrame
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    })
    
    # Sort by importance
    importance_df = importance_df.sort_values('importance', ascending=False).reset_index(drop=True)
    
    return importance_df
